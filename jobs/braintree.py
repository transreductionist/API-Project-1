"""The following module provides for updating database transactions when Braintree sales updates occur online.

For testing there is a module in the scripts folder called manage_braintree_transactions.py. There are 2 functions
there that are useful in testing. The first will create a Gift and initial transaction for existing sales on
Braintree. These sales will typically be in statuses other than authorized, there may also be refunds, disputes, and
subscriptions. Creating the initial database entries will allow the updater to run against these sales. The second
function allows sales to be returned for searches such as authorized_at and submitted_for_settlement_at.

    1. create_sales_from_existing_braintree_sales()
    2. search_at( date0, date1, search_status_at, sales )

The module here also provides for writing data to CSV files in an S3 bucket.

python -c "import jobs.braintree;jobs.braintree.manage_status_updates()"
"""
import logging
import os
import uuid
from collections import OrderedDict
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal

import braintree
from s3_web_storage.web_storage import WebStorage

from application.app import create_app
from application.exceptions.exception_critical_path import UpdaterCriticalPathError
from application.flask_essentials import database
from application.helpers.braintree_api import init_braintree_credentials
from application.helpers.build_output_file import build_flat_bytesio_csv
from application.helpers.email import send_statistics_report
from application.helpers.model_serialization import from_json
from application.models.agent import AgentModel
from application.models.gift import GiftModel
from application.models.gift_thank_you_letter import GiftThankYouLetterModel
from application.models.transaction import TransactionModel
from application.schemas.gift import GiftSchema
from application.schemas.transaction import TransactionSchema
# pylint: disable=bare-except
# flake8: noqa:E722
# pylint: disable=no-member

# Check for how the application is being run and use that.
# The environment variable is set in the Dockerfile.
if 'APP_ENV' in os.environ:
    app_config_env = os.environ[ 'APP_ENV' ]  # pylint: disable=invalid-name
else:
    app_config_env = 'DEFAULT'  # pylint: disable=invalid-name

logging.debug( '***** app.config[ ENV ]: %s', app_config_env )

app = create_app( app_config_env )  # pylint: disable=C0103

WebStorage.init_storage( app, app.config[ 'AWS_CSV_FILES_BUCKET' ], app.config[ 'AWS_CSV_FILES_PATH' ] )

init_braintree_credentials( app )

THANK_YOU_LETTER_THRESHOLD = Decimal( app.config[ 'THANK_YOU_LETTER_THRESHOLD' ] )
MODEL_DATE_STRING_FORMAT = '%Y-%m-%d %H:%M:%S'
BRAINTREE_DATE_STRING_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
BRAINTREE_CHARGEBACK_TYPE = braintree.Dispute.Kind.Chargeback
BRAINTREE_CHARGEBACK_FINE_AMOUNT = Decimal( -15.0 )

TRACKED_STATUSES = [ 'authorized_at', 'submitted_for_settlement_at', 'settled_at', 'voided_at' ]
FAILURE_STATUSES = [ 'processor_declined_at', 'gateway_rejected_at', 'failed_at', 'authorization_expired_at' ]

MERCHANT_ACCOUNT_ID = {
    app.config[ 'NUMBERSUSA' ]: 'NERF',
    app.config[ 'NUMBERSUSA_ACTION' ]: 'ACTION'
}

DISPUTE_STATUS_HISTORY = {
    'accepted': 'Lost',
    'disputed': 'Requested',
    'expired': 'Lost',
    'open': 'Accepted',
    'lost': 'Lost',
    'won': 'Won'
}

EXCLUDE_STATUSES = [
    'authorization_expired',
    'authorizing',
    'failed',
    'gateway_rejected',
    'processor_declined',
    'settlement_pending',
    'settlement_confirmed',
    'settlement_declined',
    'settling',
    'settled'
]

# Data lists for failures and sales that appear to be missing a Gift/Transaction: fields on the braintree object.
BRAINTREE_SALE_FIELDS = [
    'id', 'amount', 'created_at', 'updated_at', { 'credit_card_details': [ 'cardholder_name' ] },
    'merchant_account_id', 'refunded_transaction_id', 'service_fee_amount', 'settlement_batch_id', 'status',
    'subscription_id', 'gateway_rejection_reason', 'processor_response_text'
]

# Data lists for disputes and disputes that appear to be missing a Gift/Transaction: fields on the braintree object.
BRAINTREE_DISPUTE_FIELDS = [
    'amount', 'case_number', 'received_date', 'reply_by_date', 'amount_disputed',
    { 'transaction': [ 'amount', 'created_at', 'id' ] }, 'amount_won', 'status', 'reason', 'kind',
    'merchant_account_id', 'date_opened', 'created_at', 'updated_at'
]

# If we need to build transactions we need to know the sign to attribute to the sale amount.
MULTIPLIER_FOR_TYPE_STATUS = {
    'Gift': { 'Completed': 1 },
    'Correction': { 'Completed': 0 },
    'Refund': { 'Completed': -1 },
    'Void': { 'Completed': 1 },
    'Dispute': { 'Won': 0, 'Lost': -1, 'Requested': 1, 'Accepted': 0 },
    'Fine': { 'Completed': -1 }
}

# Get the Agent ID from the model for type Automated. This is used on both the Gift and Transaction models.
with app.app_context():
    AGENT_MODEL = AgentModel.get_agent( 'Organization', 'name', 'Donate API' )  # pylint: disable=invalid-name
    AGENT_ID = str( AGENT_MODEL.id )

# **************************************************************** #
# ***** INTERVAL FOR CRON SET HERE ******************************* #
# Here is where the interval is set. The cron job executes the script on some repeated time, e.g. every 5 minutes:
#     */5 * * * * cd /home/apeters/git/DONATE_updater && /home/apeters/git/DONATE_updater/venv/bin/python3
#         -c "import jobs.braintree;jobs.braintree.manage_status_updates()" >>
#         /home/apeters/git/DONATE_updater/cron.log 2>&1

INTERVAL = timedelta( days=30, hours=23, minutes=59, seconds=59, microseconds=999999 )

DATE1 = datetime.utcnow().replace( hour=23, minute=59, second=59, microsecond=999999 )
DATE0 = DATE1 - INTERVAL
LOG_INFO = 'Transaction updater cron job: %s ~ %s' % (
    DATE0.strftime( MODEL_DATE_STRING_FORMAT ), DATE1.strftime( MODEL_DATE_STRING_FORMAT )
)
logging.debug( 'INTERVAL: %s', INTERVAL )
logging.debug( 'DATES   : %s', LOG_INFO )

# **************************************************************** #


def manage_status_updates():
    """A top level function that calls lower level code to do the updates and handle writing files to S3."""

    dispute_data = []
    failure_data = []
    priority_dispute_data = []
    priority_sale_data = []
    with app.app_context():

        # Begin updating the database.
        logging.debug( '>>>>> 1/12 Retrieve priority sales' )
        process_new_statuses( priority_sale_data )

        logging.debug( '>>>>> 2/12 Retrieve priority disputes' )
        process_new_disputes( dispute_data, priority_dispute_data )

        logging.debug( '>>>>> 3/12 Retrieve failures' )
        process_failures( failure_data )

        # Save data to CSV files on S3.
        urls = {}
        if priority_sale_data:
            generate_priority_sale_data( priority_sale_data, urls )

        if priority_dispute_data:
            generate_priority_dispute_data( priority_dispute_data, urls )
        else:
            logging.debug( '>>>>> 6/12 No priority dispute data' )
            logging.debug( '>>>>> 7/12 No priority dispute data to save' )

        if failure_data:
            generate_failure_data( failure_data, urls )
        else:
            logging.debug( '>>>>> 8/12 No failure data' )
            logging.debug( '>>>>> 9/12 No failure data to save' )

        if dispute_data:
            generate_dispute_data( dispute_data, urls )
        else:
            logging.debug( '>>>>> 10/12 No dispute data' )
            logging.debug( '>>>>> 11/12 No dispute data to save' )

        if urls:
            logging.debug( '>>>>> 12/12 Sending emails' )
            send_statistics_report( urls )
        else:
            logging.debug( '>>>>> 12/12 No data found' )


def generate_priority_sale_data( priority_sale_data, urls ):
    """Handle the priority sale data file generation."""

    header = build_header( BRAINTREE_SALE_FIELDS, 'Note' )
    logging.debug( '>>>>> 4/12 Build priority sale file' )
    priority_sale_file_name = build_flat_bytesio_csv( priority_sale_data, header, 'priority_sale', True )
    logging.debug( '>>>>> 5/12 Save priority sale data' )
    urls[ 'priority_sale' ] = generate_url( priority_sale_file_name )
    logging.debug( '>>>>> 4/12 No priority sale data' )
    logging.debug( '>>>>> 5/12 No priority sale data to save' )


def generate_priority_dispute_data( priority_dispute_data, urls ):
    """Handle the priority dispute data file generation."""

    header = build_header( BRAINTREE_DISPUTE_FIELDS, 'Note' )
    logging.debug( '>>>>> 6/12 Build priority dispute file' )
    priority_dispute_file_name = build_flat_bytesio_csv(
        priority_dispute_data, header, 'priority_dispute', True
    )
    logging.debug( '>>>>> 7/12 Save priority dispute data' )
    urls[ 'priority_dispute' ] = generate_url( priority_dispute_file_name )


def generate_failure_data( failure_data, urls ):
    """Handle the failure data file generation."""

    header = build_header( BRAINTREE_SALE_FIELDS, 'Note' )
    logging.debug( '>>>>> 8/12 Build failure file' )
    failed_file_name = build_flat_bytesio_csv( failure_data, header, 'failed', True )
    logging.debug( '>>>>> 9/12 Save failure data' )
    urls[ 'failed' ] = generate_url( failed_file_name )


def generate_dispute_data( dispute_data, urls ):
    """Handle the dispute data file generation."""

    header = build_header( BRAINTREE_DISPUTE_FIELDS, 'Note' )
    logging.debug( '>>>>> 10/12 Build dispute file' )
    dispute_file_name = build_flat_bytesio_csv( dispute_data, header, 'dispute', True )
    logging.debug( '>>>>> 11/12 Save dispute data' )
    urls[ 'dispute' ] = generate_url( dispute_file_name )


def generate_url( file_name ):
    """Generate a pre-signed URL to download file from AWS S3"""

    url = WebStorage.generate_presigned_url(
        app.config[ 'AWS_CSV_FILES_BUCKET' ],
        app.config[ 'AWS_CSV_FILES_PATH' ] + file_name
    )
    return url


def process_failures( failure_data ):
    """Calls search_at to get sales that were declined, rejected, failed, and expired in the interval.

    :param failure_data: A list to collect failure data to pass to the CSV writer.
    :return:
    """

    sales = {}
    for status in FAILURE_STATUSES:
        search_at( DATE0, DATE1, status, sales )

    # Each failure should be written to a CSV file for further review.
    for sale_id, sale in sales.items():  # pylint: disable=unused-variable
        failure_data.append(
            get_row_of_data(
                sale,
                BRAINTREE_SALE_FIELDS,
                'Sale status: {}.'.format( sale.status )
            )
        )


def process_new_disputes( dispute_data, priority_dispute_data ):
    """Function to do the work of updating database transactions with dispute information.

    :param dispute_data: A list to collect dispute data to pass to the CSV writer.
    :param priority_dispute_data: Collect priority dispute data ( inconsistencies with database ) for CSV.
    :return:
    """

    # Disputes must be handled separately, partly because of how they are searched: effective_date of the event.
    # The format of the object returned is different then a sale is another reason to handle it separately.
    braintree_disputes = braintree.Dispute.search(
        braintree.DisputeSearch.status.in_list(
            [
                braintree.Dispute.Status.Accepted,
                braintree.Dispute.Status.Disputed,
                braintree.Dispute.Status.Expired,
                braintree.Dispute.Status.Open,
                braintree.Dispute.Status.Lost,
                braintree.Dispute.Status.Won
            ]
        ),
        braintree.DisputeSearch.effective_date.between( DATE0, DATE1 )
    )

    for dispute in braintree_disputes.disputes:

        updated_at = datetime.strptime( dispute.updated_at, BRAINTREE_DATE_STRING_FORMAT )
        if DATE0 <= updated_at <= DATE1:

            sale_id = dispute.transaction.id

            history_attributes = { 'dispute_history': {} }
            for history_item in dispute.status_history:
                history_attributes[ 'dispute_history' ][ history_item.status ] = \
                    datetime.strptime( history_item.timestamp, BRAINTREE_DATE_STRING_FORMAT )

            history_attributes[ 'dispute_kind' ] = dispute.kind

            try:
                # This is a dispute.
                transaction_initial = TransactionModel.query.filter_by( reference_number=sale_id ) \
                    .filter_by( type='Gift' ) \
                    .filter_by( status='Completed' ).one_or_none()

                if not transaction_initial:
                    priority_dispute_data.append(
                        get_row_of_data(
                            dispute,
                            BRAINTREE_DISPUTE_FIELDS,
                            'Dispute ID {} with no initial transaction.'.format( dispute.id )
                        )
                    )
                    continue
                else:
                    gift_id = transaction_initial.gift_id

                # Now update the transactions
                refunded_transaction_id = None
                transaction_models = build_transactions( dispute, history_attributes, gift_id, refunded_transaction_id )

                database.session.bulk_save_objects( transaction_models )
                database.session.commit()

                # Build CSV data.
                dispute_data.append(
                    get_row_of_data(
                        dispute,
                        BRAINTREE_DISPUTE_FIELDS,
                        'Dispute ID: {}.'.format( dispute.id )
                    )
                )
            except:  # noqa: E722
                database.session.rollback()
                logging.debug(
                    UpdaterCriticalPathError( where='disputes', type_id=sale_id ).message
                )


def process_new_statuses( priority_sale_data ):
    """Function to do the work of updating database transactions with new statuses on Braintree sales.

    :param priority_sale_data: Collect priority sale data ( inconsistencies with database ) for CSV.
    :return:
    """

    # Get all the updated sales in the interval.
    sales = {}
    for status in TRACKED_STATUSES:
        search_at( DATE0, DATE1, status, sales )

    for sale_id, sale in sales.items():

        # We need to know what kind of sale this is.
        disbursement_date = sale.disbursement_details.disbursement_date

        history_attributes = {}
        for history_item in sale.status_history:
            history_attributes[ history_item.status ] = history_item.timestamp
        if disbursement_date:
            history_attributes[ 'disbursed' ] = disbursement_date
        history_attributes = { 'sale': history_attributes }

        if sale.recurring:
            manage_recurring_sales( sale_id, sale, history_attributes, priority_sale_data )

        elif 'authorized' in history_attributes[ 'sale' ] and not sale.refunded_transaction_id:
            manage_authorized_not_refund( sale_id, sale, history_attributes, priority_sale_data )

        elif 'authorized' not in history_attributes[ 'sale' ] and sale.refunded_transaction_id:
            manage_not_authorized_refund( sale_id, sale, history_attributes, priority_sale_data )

        try:
            database.session.commit()
        except:  # noqa: E722
            database.session.rollback()
            logging.debug(
                UpdaterCriticalPathError( where='process_new_statuses', type_id=sale_id ).message
            )


def manage_recurring_sales( sale_id, sale, history_attributes, priority_sale_data ):
    """Logic for one item in the loop over sales for new statuses when they are recurring.

    :param sale_id: The key of the loop, the Braintree sale ID.
    :param sale: The value for the loop, a Braintree sale.
    :param history_attributes: The history attributes for the sale.
    :return:
    """

    try:
        # Try to get the user ID from previous gifts.
        gifts_with_subscription_id = GiftModel.query.filter_by( recurring_subscription_id=sale.subscription_id ).all()
        user_id = None
        for gift in gifts_with_subscription_id:
            if gift.user_id and gift.user_id != 999999999:
                user_id = gift.user_id
        if not user_id:
            user_id = 999999999

        if user_id == 999999999:
            priority_sale_data.append(
                get_row_of_data(
                    sale,
                    BRAINTREE_SALE_FIELDS,
                    'Recurring transaction without an initial transaction in database.'
                )
            )
        else:
            try:
                # This is a subscription and needs its own gift if not already present.
                transaction_initial = TransactionModel.query.filter_by( reference_number=sale_id ) \
                    .filter_by( type='Gift' ) \
                    .filter_by( status='Completed' ).one_or_none()

                if not transaction_initial:
                    gift_dict = {
                        'id': None,
                        'searchable_id': uuid.uuid4(),
                        'user_id': user_id,
                        'customer_id': sale.customer[ 'id' ],
                        'method_used': 'Admin-Entered Credit Card',
                        'sourced_from_agent_id': AGENT_ID,
                        'given_to': MERCHANT_ACCOUNT_ID[ sale.merchant_account_id ],
                        'recurring_subscription_id': sale.subscription_id
                    }
                    gift_model = from_json( GiftSchema(), gift_dict )
                    database.session.add( gift_model.data )
                    database.session.flush()
                    database.session.commit()
                    gift_id = gift_model.data.id
                else:
                    gift_id = transaction_initial.gift_id

                transaction_models = build_transactions(
                    sale, history_attributes, gift_id, sale.refunded_transaction_id
                )
                database.session.bulk_save_objects( transaction_models )
            except:  # noqa: E722
                database.session.rollback()
                logging.debug(
                    UpdaterCriticalPathError( where='manage_recurring_sales rolling back', type_id=sale_id ).message
                )
    except:  # noqa: E722
        logging.debug(
            UpdaterCriticalPathError( where='manage_recurring_sales', type_id=sale_id ).message
        )


def manage_authorized_not_refund( sale_id, sale, history_attributes, priority_sale_data ):
    """Logic for one item in the loop over sales that are not refunds and have status authorized.

    :param sale_id: The key of the loop, the Braintree sale ID.
    :param sale: The value for the loop, a Braintree sale.
    :param history_attributes: The history attributes for the sale.
    :return:
    """

    # This is a sale and should definitely have a transaction in the database.
    try:
        transaction_initial = TransactionModel.query.filter_by( reference_number=sale_id ) \
            .filter_by( type='Gift' ) \
            .filter_by( status='Completed' ).one_or_none()

        if not transaction_initial:
            priority_sale_data.append(
                get_row_of_data(
                    sale,
                    BRAINTREE_SALE_FIELDS,
                    'Authorized in history without an initial transaction in database.'
                )
            )
            return

        gift_id = transaction_initial.gift_id
        transaction_models = build_transactions(
            sale, history_attributes, gift_id, sale.refunded_transaction_id
        )
        database.session.bulk_save_objects( transaction_models )
    except:  # noqa: E722
        database.session.rollback()
        logging.debug(
            UpdaterCriticalPathError( where='manage_authorized_not_refund', type_id=sale_id ).message
        )


def manage_not_authorized_refund( sale_id, sale, history_attributes, priority_sale_data ):
    """Logic for one item in the loop over sales that are refunds without authorized in the history.

    :param sale_id: The key of the loop, the Braintree sale ID.
    :param sale: The value for the loop, a Braintree sale.
    :param history_attributes: The history attributes for the sale.
    :return:
    """

    # This is a refund and should have both a parent/refund transaction in the database.
    # If one doesn't exist back fill it.
    try:
        transaction_parent = TransactionModel.query.filter_by( reference_number=sale.refunded_transaction_id ) \
            .filter_by( type='Gift' ) \
            .filter_by( status='Completed' ).one_or_none()

        if not transaction_parent:
            priority_sale_data.append(
                get_row_of_data(
                    sale,
                    BRAINTREE_SALE_FIELDS,
                    'Refunded transaction without an initial parent transaction in database.'
                )
            )
            return

        gift_id = transaction_parent.gift_id
        transaction_models = build_transactions(
            sale, history_attributes, gift_id, sale.refunded_transaction_id
        )
        database.session.bulk_save_objects( transaction_models )
    except:  # noqa: E722
        database.session.rollback()
        logging.debug(
            UpdaterCriticalPathError( where='manage_not_authorized_refund', type_id=sale_id ).message
        )


def build_transactions(  # pylint: disable=too-many-locals
        sale_or_dispute, history_attributes, gift_id, refunded_transaction_id
):
    """Given a sale or dispute, along with some other data build a transaction for the sale.

    :param sale_or_dispute: This is either a sale or dispute Braintree object.
    :param history_attributes: The parsed history on the sale or dispute.
    :param gift_id: The gift ID the transaction is attached to.
    :param refunded_transaction_id: The parent ID to a refunded transaction.
    :return:
    """

    transaction_models = []

    is_dispute, history_attributes_sorted = get_sorted_history_attributes(
        transaction_models, sale_or_dispute, history_attributes, gift_id
    )

    total_amount = get_total_amount( gift_id )

    for status, timestamp in history_attributes_sorted.items():
        amount = Decimal( 0 )
        fee = Decimal( 0 )
        transaction_status_type = {}
        if is_dispute:
            transaction_status_type[ 'type' ] = 'Dispute'
            transaction_status_type[ 'status' ] = DISPUTE_STATUS_HISTORY[ status ]
            if sale_or_dispute.amount_disputed:
                amount = sale_or_dispute.amount_disputed
        else:
            transaction_status_type = get_transaction_status_type( status, refunded_transaction_id )
            if not transaction_status_type:
                continue
            if sale_or_dispute.amount:
                amount = sale_or_dispute.amount
            if sale_or_dispute.service_fee_amount:
                fee = sale_or_dispute.service_fee_amount

        transaction_type = transaction_status_type[ 'type' ]
        transaction_status = transaction_status_type[ 'status' ]

        # See if a transaction already exists.
        transaction = TransactionModel.query.filter_by( reference_number=sale_or_dispute.id ) \
            .filter_by( type=transaction_type ) \
            .filter_by( status=transaction_status ).one_or_none()

        if not transaction:

            # Increment/decrement the total amount currently on the gift given its type and status.
            total_amount += MULTIPLIER_FOR_TYPE_STATUS[ transaction_type ][ transaction_status ] * amount

            transaction_dict = {
                'gift_id': gift_id,
                'date_in_utc': timestamp.strftime( MODEL_DATE_STRING_FORMAT ),
                'enacted_by_agent_id': AGENT_ID,
                'type': transaction_type,
                'status': transaction_status,
                'reference_number': sale_or_dispute.id,
                'gross_gift_amount': total_amount,
                'fee': fee,
                'notes': 'Automated creation' if not refunded_transaction_id
                         else 'Automated creation: parent ID is {}.'.format( refunded_transaction_id )
            }
            transaction_model = from_json( TransactionSchema(), transaction_dict )
            transaction_models.append( transaction_model.data )

            # If the gift amount >= $100 ( current threshold ), add to gift_thank_you_letter table
            if ( Decimal( transaction_dict[ 'gross_gift_amount' ] ) >= THANK_YOU_LETTER_THRESHOLD ) \
                    and ( type == 'Gift' and status == 'Completed' ):
                database.session.add( GiftThankYouLetterModel( gift_id=transaction_dict[ 'gift_id' ] ) )

    return transaction_models


def get_sorted_history_attributes( transaction_models, sale_or_dispute, history_attributes, gift_id ):
    """Sort the history attributes and determine if a dispute or sale.

    :param transaction_models: The collected transaction_models.
    :param sale_or_dispute: The Braintree sale or dispute.
    :param history_attributes: The history attributes on the sale or dispute.
    :param gift_id: The gift ID.
    :return:
    """

    is_dispute = False
    if 'dispute_history' in history_attributes:
        is_dispute = True
        # Before going on to updating the transactions on the gift make sure the chargeback fine is attached.
        dispute_assess_fine( transaction_models, sale_or_dispute, history_attributes, gift_id )
        history_attributes = history_attributes[ 'dispute_history' ]
    elif 'sale' in history_attributes:
        history_attributes = history_attributes[ 'sale' ]
    # Make sure the attributes are sorted by date so they are in the right order.
    history_attributes_sorted = OrderedDict( sorted( history_attributes.items(), key=lambda x: x[ 1 ] ) )
    return is_dispute, history_attributes_sorted


def get_total_amount( gift_id ):
    """Get the current total gross_gift_amount on the gift.

    :param gift_id: The gift ID.
    :return: Current total_amount on gift.
    """

    # The current gross_gift_amount must be determined from the gift_id.
    # Remember that refunds and disputes are separate "transactions."
    transactions = TransactionModel.query.filter_by( gift_id=gift_id ).all()
    total_amount = Decimal( 0.00 )
    if transactions:
        the_date = None
        for transaction in transactions:
            if not the_date or transaction.date_in_utc > the_date:
                the_date = transaction.date_in_utc
                total_amount = Decimal( transaction.gross_gift_amount )
    return total_amount


def dispute_assess_fine( transaction_models, sale_or_dispute, history_attributes, gift_id ):
    """Build the transaction for the fine if the dispute is a chargeback.

    The history_status on a dispute does not contain information about fines. The Dispute kind ( dispute.kind )
    indicates whether the dispute is a chargeback and if it is Braintree assesses a $15 fine no matter what. Because
    it is not on the status we have to check the kind and if a chargeback has the fine already been attached to the
    gift. If it hasn't we use the datetime stamp of the Open history status to set the date_in_utc. If that is
    missing we revert to datetime.utcnow().

    :param transaction_models: Transaction models being built for disputes and sales.
    :param sale_or_dispute: The dispute
    :param history_attributes: The history status
    :param gift_id: The gift_id associated with the Braintree reference number
    :return:
    """
    if history_attributes[ 'dispute_kind' ] == BRAINTREE_CHARGEBACK_TYPE:
        transaction_for_fine = TransactionModel.query.filter_by( reference_number=sale_or_dispute.id ) \
            .filter_by( type='Fine' ) \
            .filter_by( status='Completed' ).one_or_none()
        if not transaction_for_fine:
            if 'open' in history_attributes[ 'dispute_history' ]:
                date_in_utc = history_attributes[ 'dispute_history' ][ 'open' ].strftime( MODEL_DATE_STRING_FORMAT )
            else:
                date_in_utc = datetime.utcnow()
            transaction_dict = {
                'gift_id': gift_id,
                'date_in_utc': date_in_utc,
                'enacted_by_agent_id': AGENT_ID,
                'type': 'Fine',
                'status': 'Completed',
                'reference_number': sale_or_dispute.id,
                'gross_gift_amount': Decimal( 0 ),
                'fee': BRAINTREE_CHARGEBACK_FINE_AMOUNT,
                'notes': 'Automated creation of chargeback dispute fine'
            }
            transaction_model = from_json( TransactionSchema(), transaction_dict )
            transaction_models.append( transaction_model.data )


def get_transaction_status_type( sale_status, refunded_transaction_id ):
    """Get the transaction status given the Braintree sale status and whether it is a refund or not.


    :param sale_status: The status of the Braintree sale.
    :param refunded_transaction_id: The parent ID for the refunded transaction. May be None.
    :return:
    """

    type_status = {}

    if sale_status in EXCLUDE_STATUSES:
        return type_status

    if refunded_transaction_id:
        if sale_status == 'submitted_for_settlement':
            type_status = { 'type': 'Refund', 'status': 'Completed' }
        elif sale_status == 'settled':
            type_status = { 'type': 'Refund', 'status': 'Completed' }
    else:
        if sale_status == 'authorized':
            type_status = { 'type': 'Gift', 'status': 'Completed' }
        elif sale_status == 'submitted_for_settlement':
            type_status = {}
        elif sale_status == 'settled':
            type_status = { 'type': 'Gift', 'status': 'Completed' }

    if sale_status == 'voided':
        type_status = { 'type': 'Void', 'status': 'Completed' }
    elif sale_status == 'disbursed':
        type_status = { 'type': 'Deposit to Bank', 'status': 'Completed' }

    return type_status


def get_row_of_data( braintree_obj, fields, note=None ):
    """Given a Braintree object build a row of data from the defined fields.

    :param braintree_obj: Dispute or sale.
    :param fields: Something like BRAINTREE_SALE_FIELDS, i.e. the fields to include from the object passed.
    :param note: The text for an additional note to be included in the row of data if provided.
    :return: A row of data.
    """

    row = []
    for attribute in fields:
        if isinstance( attribute, dict ):
            attribute_obj_name = list( attribute.keys() )[ 0 ]
            attribute_obj = getattr( braintree_obj, attribute_obj_name )
            attribute_obj_attributes = attribute[ attribute_obj_name ]
            for attribute_obj_attribute in attribute_obj_attributes:
                value = convert_value( getattr( attribute_obj, attribute_obj_attribute ) )
                row.append( value )
        else:
            value = convert_value( getattr( braintree_obj, attribute ) )
            row.append( value )

    if note:
        row.append( note )

    return row


def build_header( fields, note_title=None ):
    """Builder a list representing the CSV header from the fields.

    :param fields: Something like BRAINTREE_SALE_FIELDS, i.e. the fields to include from the object passed.
    :param note_title: A header title for a note.
    :return:
    """

    header = []
    for attribute in fields:
        if isinstance( attribute, dict ):
            attribute_obj_name = list( attribute.keys() )[ 0 ]
            attribute_obj_attributes = attribute[ attribute_obj_name ]
            for attribute_obj_attribute in attribute_obj_attributes:
                header.append( '{}.{}'.format( attribute_obj_name, attribute_obj_attribute ) )
        else:
            header.append( attribute )

    if note_title:
        header.append( note_title )

    return header


def convert_value( value ):
    """A small helper function to convert a value to a string.

    :param value: Used primarily to convert a Date or Decimal to a string.
    :return: The value as string.
    """

    if isinstance( value, date ):
        value = value.strftime( BRAINTREE_DATE_STRING_FORMAT )
    elif isinstance( value, Decimal ):
        value = str( value )
    elif not value:
        value = ''

    return value


def search_at( date0, date1, search_status_at, sales ):
    """Returns a list of sales for search_status_at between the dates provided:

        authorization_expired_at
        authorized_at
        created_at
        failed_at
        gateway_rejected_at
        processor_declined_at
        settled_at
        submitted_for_settlement_at ( Useful for getting refunds that go right into a submitted_for_settlement status. )
        voided_at

    :param date0: Initial date
    :param date1: Final date
    :param search_status_at: One from the list given above.
    :param sales: The sales found between those dates.
    :return:
    """

    search_obj_at = getattr( braintree.TransactionSearch, search_status_at )
    braintree_transactions = braintree.Transaction.search(
        search_obj_at.between( date0, date1 )
    )
    for braintree_transaction in braintree_transactions:
        if braintree_transaction.id not in sales:
            sales[ braintree_transaction.id ] = braintree_transaction


if __name__ == '__main__':
    manage_status_updates()
