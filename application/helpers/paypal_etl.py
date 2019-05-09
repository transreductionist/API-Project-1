"""Controllers for Flask-RESTful PayPalETL resources: handle the business logic for the endpoint."""
import csv
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation

from flask import current_app
from s3_web_storage.web_storage import WebStorage
from sqlalchemy.exc import SQLAlchemyError

from application.exceptions.exception_paypal_etl import PayPalETLFileTypeError
from application.exceptions.exception_paypal_etl import PayPalETLInvalidColumnsError
from application.exceptions.exception_paypal_etl import PayPalETLNoFileDataError
from application.exceptions.exception_paypal_etl import PayPalETLNoFileKeyError
from application.exceptions.exception_paypal_etl import PayPalETLOnCommitError
from application.exceptions.exception_paypal_etl import PayPalETLTooManyRowsError
from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from application.helpers.ultsys_user import get_ultsys_user
from application.models.agent import AgentModel
from application.models.paypal_etl import PaypalETLModel
from application.models.transaction import TransactionModel
from application.models.unresolved_paypal_etl_transaction import UnresolvedPaypalETLTransactionModel
from application.schemas.caged_donor import CagedDonorSchema
from application.schemas.gift import GiftSchema
from application.schemas.transaction import TransactionSchema
from application.schemas.unresolved_paypal_etl_transaction import UnresolvedPaypalETLTransactionSchema

REQUIRED_COLUMNS = {
    'gross',
    'fee',
    'from_email_address',
    'transaction_id',
    'date',
    'time',
    'time_zone',
    'name',
    'type',
    'status',
    'transaction_id',
    'reference_txn_id',
    'to_email_address',
    'subject'
}

VALID_GIFT_TRANSACTION_TYPES = {
    'Donation Received',
    'Shopping Cart Payment Received',
    'Virtual Terminal Transaction',
    'Mobile Donation Received',
    'Virtual Terminal Payment',
    'Website Payments Pro API Solution',
    'Donation Payment',
    'Direct Credit Card Payment',
    'Recurring Payment Received',
    'Subscription Payment Received',
    'Subscription Payment',
    'Website Payments Pro API Solution',
    'Express Checkout Payment Received',
    'Mobile Express Checkout Payment Received',
    'Payment Received',
    'Web Accept Payment Received'
}

USELESS_PAYPAL_TRANSACTION_TYPES = {
    'Authorization',
    'Cancelled Fee',
    'Cancelled Transfer',
    'eBay Payment Sent',
    'PayPal Balance Adjustment',
    'Received Settlement Withdrawal',
    'Settlement Withdraw to Payment Processor',
    'Withdraw Funds to Bank Account',
    'Currency Conversion',
    'Preapproved Payment Sent',
    'Add Funds from a Bank Account',
    'Bank Deposit to PP Account',
    'eCheck Add Funds from a Bank Account',
    'Donation Sent',
    'Payment Sent',
    'Web Accept Payment Sent',
    'Express Checkout Payment Sent',
    'Shopping Cart Payment Sent',
    'Correction',
    'Update to Payment Received',
    'PayPal card confirmation refund',
    'Update to eCheck Received',
    'Update to eCheck Sent',
    'Void',
    'Auto-sweep',
    'General Withdrawal'
}

TRANSACTION_STATUS = {
    'Accepted',
    'Completed',
    'Declined',
    'Denied',
    'Failed',
    'Forced',
    'Lost',
    'Refused',
    'Requested',
    'Won'
}

REFUND_PAYPAL_TRANSACTION_TYPES = {
    'Refund',
    'Payment Refund'
}

DISPUTE_PAYPAL_TRANSACTION_TYPES = {
    'Payment Review',
    'Hold on Balance for Dispute Investigation'
}


def process_paypal_etl( enacted_by_agent_id, reader_list, file_storage ):
    """Handle the logic for PayPal ETL.

    :param enacted_by_agent_id: The administrative user ID.
    :param reader_list: The CSV validated and converted to a list of ordered dictionaries.
    :param file_storage_name: The file storage name.
    :return:
    """

    data_from_models = get_data_from_models()
    ids = {
        'transaction': data_from_models[ 'transaction_ids' ],
        'unresolved_transaction': data_from_models[ 'unresolved_transaction_ids' ]
    }

    agent_emails = get_agent_emails()

    # Using for SQLAlchemy bulk_save_objects().
    bulk_objects = {
        'transaction': [],
        'caged_donor': [],
        'unresolved_transaction': []
    }

    # Start the loop.
    for row in reader_list:

        if row[ 'transaction_id' ] in data_from_models[ 'transaction_ids' ]:
            # This transaction already exists in our database.
            continue

        transaction_type = row[ 'type' ]

        if transaction_type in VALID_GIFT_TRANSACTION_TYPES:
            valid_paypal_transaction(
                row,
                enacted_by_agent_id,
                agent_emails,
                ids,
                bulk_objects
            )
        elif transaction_type in REFUND_PAYPAL_TRANSACTION_TYPES:
            refund_paypal_transaction(
                row,
                enacted_by_agent_id,
                ids,
                bulk_objects
            )
        elif transaction_type in DISPUTE_PAYPAL_TRANSACTION_TYPES:
            # Handle the PayPal disputes.
            dispute_paypal_transaction(
                row,
                enacted_by_agent_id,
                ids,
                bulk_objects
            )
        elif transaction_type in USELESS_PAYPAL_TRANSACTION_TYPES:
            # Culling extraneous transaction types from PayPal.
            continue
        else:
            # CSV file might come with some types we don't know how to process yet.
            bulk_objects[ 'unresolved_transaction' ] += filter(
                None,
                [
                    generate_unresolved_transaction(
                        row, data_from_models[ 'unresolved_transaction_ids' ], enacted_by_agent_id
                    )
                ]
            )

    # Store into PayPal_ETL table.
    file_storage_name = file_storage.filename
    paypal_etl = PaypalETLModel()
    paypal_etl.enacted_by_agent_id = enacted_by_agent_id
    file_info = file_storage_name.split( '.' )
    file_date = datetime.utcnow()
    file_name = '.'.join( file_info[ :-1 ] ) + '_' + file_date.strftime( '%Y-%m-%d %H:%M:%S' ) + '.' + file_info[ -1 ]
    paypal_etl.file_name = file_name
    paypal_etl.date_in_utc = file_date
    database.session.add( paypal_etl )

    # Bulk save various objects.
    database.session.bulk_save_objects( bulk_objects[ 'transaction' ] )
    database.session.bulk_save_objects( bulk_objects[ 'caged_donor' ] )
    database.session.bulk_save_objects( bulk_objects[ 'unresolved_transaction' ] )

    # Commit to the database.
    try:
        database.session.commit()
    except SQLAlchemyError:
        database.session.rollback()
        raise PayPalETLOnCommitError
    else:
        # Store file on AWS S3 and return link.
        file_storage.seek( 0 )
        WebStorage.init_storage(
            current_app, current_app.config.get( 'AWS_CSV_FILES_BUCKET' ),
            current_app.config.get( 'AWS_CSV_FILES_PATH' )
        )
        metadata = ( 'Paypal ETL', file_name )
        WebStorage.save(
            file_name,
            file_storage.read(),
            metadata
        )
        return True


def validate_file_data_storage( file_data ):
    """Validate the file storage object passed here from the front-end.

    :param file_data: A file storage object.
    :return: The CSV file as a list of Ordered Dictionaries.
    """

    # Get the key from the file storage object.
    file_storage_keys = [ file_key for file_key in file_data.keys() ]
    if file_storage_keys:
        file_storage_key = file_storage_keys[ 0 ]
    else:
        raise PayPalETLNoFileKeyError

    file_storage = file_data[ file_storage_key ]

    # Only process CSV file types.
    if not file_storage.filename.lower().endswith( 'csv' ):
        raise PayPalETLFileTypeError

    csv_file = ( line.decode( 'utf-8', errors='ignore' ) for line in file_storage )
    reader_dict = csv.DictReader( csv_file )

    # Rename the columns to NUSA names before validating the mandatory columns.
    rename_fields_name( reader_dict )

    # Turn the dictionary into a list for simple iteration.
    reader_list = list( reader_dict )
    len_reader_list = len( reader_list )

    # If no data is in the file raise an error.
    if len_reader_list < 1:
        raise PayPalETLNoFileDataError

    # If too many rows are in the file raise an error.
    if len_reader_list > 200000:
        raise PayPalETLTooManyRowsError

    # Check if the CSV file has all mandatory columns present in the header.
    for column in REQUIRED_COLUMNS:
        if column not in reader_list[ 0 ]:
            raise PayPalETLInvalidColumnsError

    return { 'reader_list': reader_list, 'file_storage': file_storage }


def rename_fields_name( reader_dict ):
    """PayPal CSV file returns columns as Name, From.Email.Address, etc. which do not fit our naming convention."""

    # REQUIRED_COLUMNS is a set we will need an index, and so convert to a list.
    columns = list( REQUIRED_COLUMNS )

    # Our test cases will consist of column names that are all lower case and have no punctuation.
    test_cases = [ ''.join( character for character in column if character.isalnum() ) for column in columns ]

    # Loop over field names and convert to a test string and then compare against our test cases.
    fieldnames = []
    for name in reader_dict.fieldnames:
        test_case = ''.join( character for character in name.lower() if character.isalnum() )
        if test_case in test_cases:
            fieldnames.append( columns[ test_cases.index( test_case ) ] )
        else:
            fieldnames.append( name )

    reader_dict.fieldnames = fieldnames


def get_data_from_models():
    """Return the model data required for processing PayPal data."""

    # Get transactions: avoid duplicate
    transaction_ids = TransactionModel.query.with_entities(
        TransactionModel.gift_id, TransactionModel.reference_number
    ).all()

    # Get all is faster than doing individual query. After create a transaction--> add transaction_id here.
    transaction_ids = { transaction_id[ 1 ]: transaction_id[ 0 ] for transaction_id in transaction_ids }

    # Get unresolved transactions: avoid duplicate.
    unresolved_transaction_ids = UnresolvedPaypalETLTransactionModel.query.with_entities(
        UnresolvedPaypalETLTransactionModel.transaction_id
    ).all()

    unresolved_transaction_ids = {
        unresolved_transaction_id[ 0 ] for unresolved_transaction_id in unresolved_transaction_ids
    }

    return {
        'transaction_ids': transaction_ids,
        'unresolved_transaction_ids': unresolved_transaction_ids
    }


def get_agent_emails():
    """Return the Agent emails."""

    # Get required agent email addresses.
    agents = AgentModel.query.all()
    agents = { agent.name: agent.id for agent in agents }
    return {
        'paypal@numbersusa.com': agents.get( 'PayPal (COMBINED)' ),  # pylint: disable=nusa-whitespace-checker
        'paypal_action@numbersusa.com': agents.get( 'PayPal (ACTION)' ),  # pylint: disable=nusa-whitespace-checker
        'paypal_nerf@numbersusa.com': agents.get( 'PayPal (NERF)' )  # pylint: disable=nusa-whitespace-checker
    }


def valid_paypal_transaction(
        row,
        enacted_by_agent_id,
        agent_emails,
        ids,
        bulk_objects
):
    """Build the valid PayPal gifts/transactions.

    :param row: A row of CSV data.
    :param enacted_by_agent_id: The admin user making the download of PayPal data..
    :param agent_emails: The agent emails needed here.
    :param ids: The collected transaction and unresolved transaction IDs.
    :param bulk_objects: The lists for bulk saving.
    :return:
    """

    # This is a gift.
    try:
        # The returned Ultsys user object is something like: { 'ID': -999 }.
        user = get_ultsys_user( { 'email': { 'eq': row[ 'from_email_address' ] } } ).json()[ 0 ]
    except ( AttributeError, IndexError, KeyError ):
        user = None

    gift_payload_user_id = user[ 'ID' ] if user else -1

    given_to = determine_given_to( row )

    gift_payload = {
        'user_id': gift_payload_user_id,
        'method_used': 'Admin-Entered Credit Card',
        'sourced_from_agent_id': agent_emails.get( row[ 'to_email_address' ] ),
        'given_to': given_to
    }

    # Subscription Number is optional.
    subscription_number = row.get( 'subscription_number' )
    if subscription_number and subscription_number != 'NA':
        gift_payload[ 'recurring_subscription_id' ] = subscription_number

    gift_schema = from_json( GiftSchema(), gift_payload )
    gift_model = gift_schema.data

    # Need Gift ID to associate with transaction. Need to add and flush here --> slow.
    # Anyone know how to do it better?
    database.session.add( gift_model )
    database.session.flush()

    transaction_model = generate_a_transaction(
        row, ids[ 'transaction' ], { 'agent_id': enacted_by_agent_id, 'type': 'Gift', 'gift_id': gift_model.id }
    )

    if user and given_to == 'TBD':
        transaction_model.notes = 'Can not determine whether the gift belongs to ACTION or NERF with user_id: {}'\
            .format( user[ 'ID' ] )

    bulk_objects[ 'transaction' ].append( transaction_model )

    # Caging if do not know user or given_to
    if gift_payload_user_id == -1 or given_to == 'TBD':
        caged_donor_model = generate_caged_donor( row )
        caged_donor_model.gift_id = gift_model.id
        caged_donor_model.gift_searchable_id = gift_model.searchable_id
        bulk_objects[ 'caged_donor' ].append( caged_donor_model )

        ids[ 'transaction' ][ row[ 'transaction_id' ] ] = gift_model.id


def refund_paypal_transaction(
        row,
        enacted_by_agent_id,
        ids,
        bulk_objects
):
    """Build the refund type PayPal gifts/transactions.

    :param row: A row of CSV data.
    :param enacted_by_agent_id: The administrative user ID.
    :param ids: The collected transaction and unresolved transaction IDs.
    :param bulk_objects: The lists for bulk saving.
    :return:
    """

    # The refund type should come with Transaction.ID & Reference.Txn.ID. The Reference.Txn.ID refer back to
    # the original transaction ( donation ). Check it Reference.Txn.ID exist in the transaction_ids yet.
    # If not, can not refund a non-exist ( yet ) transaction ( do not know gift_id ) --> log it somewhere

    transaction_ids = ids[ 'transaction' ]
    unresolved_transaction_ids = ids[ 'unresolved_transaction' ]
    transaction_object = bulk_objects[ 'transaction' ]
    unresolved_transaction_objects = bulk_objects[ 'unresolved_transaction' ]

    if row[ 'reference_txn_id' ] not in transaction_ids:
        unresolved_transaction_objects += filter(
            None, [ generate_unresolved_transaction( row, unresolved_transaction_ids, enacted_by_agent_id ) ]
        )
    else:
        # Make a refund transaction
        transaction_object.append(
            generate_a_transaction( row, transaction_ids, { 'agent_id': enacted_by_agent_id, 'type': 'Refund' } ) )
        transaction_ids[ row[ 'transaction_id' ] ] = transaction_ids.get( row[ 'reference_txn_id' ] )


def dispute_paypal_transaction(
        row,
        enacted_by_agent_id,
        ids,
        bulk_objects
):
    """Build the dispute type PayPal gifts/transactions.

    :param row: A row of CSV data.
    :param enacted_by_agent_id: The administrative user ID.
    :param ids: The collected transaction and unresolved transaction IDs.
    :param bulk_objects: The lists for bulk saving.
    :return:
    """

    transaction_ids = ids[ 'transaction' ]
    unresolved_transaction_ids = ids[ 'unresolved_transaction' ]
    transaction_object = bulk_objects[ 'transaction' ]
    unresolved_transaction_objects = bulk_objects[ 'unresolved_transaction' ]

    # Dispute
    if row[ 'reference_txn_id' ] not in transaction_ids:
        unresolved_transaction_objects += filter(
            None, [ generate_unresolved_transaction( row, unresolved_transaction_ids, enacted_by_agent_id ) ] )
    else:
        # Make a dispute transaction
        transaction_object.append(
            generate_a_transaction( row, transaction_ids, { 'agent_id': enacted_by_agent_id, 'type': 'Dispute' } )
        )
        transaction_ids[ row[ 'transaction_id' ] ] = transaction_ids.get( row[ 'reference_txn_id' ] )


def determine_given_to( transaction ):
    """Given a transaction determine if the gift should belong to ACTION, NERF or it should be caging."""

    to_email = transaction[ 'to_email_address' ]
    given_to = 'TBD'
    if to_email == 'paypal_action@numbersusa.com':
        given_to = 'ACTION'
    elif to_email == 'paypal_nerf@numbersusa.com':
        given_to = 'NERF'
    elif to_email == 'paypal@numbersusa.com':
        # combine --> using Subject to decide if the gift belong to ACTION or GIFT or CAGING.
        subject = transaction[ 'subject' ].lower()
        if subject.find( 'act' ) >= 0:
            given_to = 'ACTION'
        elif subject.find( 'nerf' ) >= 0 or subject.find( 'found' ) >= 0 or subject.find( 'educat' ) >= 0:
            given_to = 'NERF'

    return given_to


def process_name( name ):
    """Why not just give me first_name, last_name and middle name columns instead of JUST Name."""

    try:
        name = name.split()
        len_name = len( name )
    except AttributeError:
        return '', ''

    if len_name < 1:
        return '', ''

    if len_name < 2:
        return name[ 0 ], ''

    if len_name < 3:
        return name[ 0 ], name[ 1 ]

    # name has more than or equal to 3
    return ' '.join( name[ :-1 ] ), name[ -1 ]


def process_decimal_amount( amount ):
    """
    Paypal sometimes return weird stuff such as '...' for Fee.
    Our database is designed with Decimal type for Fee. Can not store '...' in db.
    Make it 0 as Fee?
    """

    try:
        # Remove , from the amount: 1,000 --> 1000.
        res = Decimal( amount.replace( ',', '' ) )
    except InvalidOperation:
        return Decimal( 0 )
    return res


def process_date_time( date, time ):
    """
    Paypal csv files return date as both 1/1/2018 and 1/1/18.
    Need 2 format to process this.
    """

    year_4_digits = '%m/%d/%Y %H:%M:%S'
    year_2_digits = '%m/%d/%y %H:%M:%S'
    year = date.split( '/' )[ -1 ]
    len_year = len( year )
    if len_year > 2:
        format_date_time = year_4_digits
    else:
        format_date_time = year_2_digits
    return datetime.strptime( date + ' ' + time, format_date_time ).strftime( '%Y-%m-%d %H:%M:%S' )


def process_transaction_status( status ):
    """PayPal sometime return status not in out Enum types."""

    if status in TRANSACTION_STATUS:
        return status
    return 'Completed'


def generate_a_transaction(
        row,
        transaction_ids,
        transaction_params
):
    """

    :param row: A row from the CSV.
    :param transaction_ids: The transaction IDs.
    :param transaction_params: agent_id, transaction type, notes, and the gift ID.
    :return:
    """

    if 'gift_id' not in transaction_params or not transaction_params[ 'gift_id' ]:
        gift_id = transaction_ids.get( row[ 'reference_txn_id' ] )
    else:
        gift_id = transaction_params[ 'gift_id' ]

    if 'notes' not in transaction_params:
        notes = 'from csv upload'
    else:
        notes = transaction_params[ 'notes' ]

    transaction_payload = {
        'gift_id': gift_id,
        'date_in_utc': process_date_time( row[ 'date' ], row[ 'time' ] ),
        'enacted_by_agent_id': transaction_params[ 'agent_id' ],
        'type': transaction_params[ 'type' ],
        'status': process_transaction_status( row[ 'status' ] ),
        'reference_number': row[ 'transaction_id' ],
        'gross_gift_amount': process_decimal_amount( row[ 'gross' ] ),
        'fee': process_decimal_amount( row[ 'fee' ] ),
        'notes': notes
    }
    transaction_schema = from_json( TransactionSchema(), transaction_payload )
    transaction_model = transaction_schema.data
    return transaction_model


def generate_unresolved_transaction( row, unresolved_transaction_ids, agent_id ):
    """Generate an unresolved transaction."""

    if row[ 'transaction_id' ] not in unresolved_transaction_ids:
        unresolved_transaction_payload = row.copy()  # shallow copy here is fine ( no nested structure )
        unresolved_transaction_payload[ 'enacted_by_agent_id' ] = agent_id
        unresolved_transaction_schema = from_json(
            UnresolvedPaypalETLTransactionSchema(),
            unresolved_transaction_payload
        )
        unresolved_transaction_model = unresolved_transaction_schema.data
        return unresolved_transaction_model
    return None


def generate_caged_donor( row ):
    """Generate caged donor."""

    user_email_address = row[ 'from_email_address' ]
    user_first_name, user_last_name = process_name( row[ 'name' ] )
    caged_donor_payload = {
        'user_email_address': user_email_address,
        'user_first_name': user_first_name,
        'user_last_name': user_last_name,
    }

    # The following columns/fields might be optional from CSV files:
    # - address_line_1 --> user_address
    # - state_province_region_county_territory_prefecture_republic --> user_state ( 2 )
    # - town_city --> user_city
    # - zip_postal_code( may have 5 or 9 ) --> user_zipcode ( 5 )

    user_address = row.get( 'address_line_1' )
    user_state = row.get( 'state_province_region_county_territory_prefecture_republic' )
    user_city = row.get( 'town_city' )
    user_zipcode = row.get( 'zip_postal_code' )
    if user_address and user_address != 'NA':
        caged_donor_payload[ 'user_address' ] = user_address
    if user_state and user_state != 'NA':
        caged_donor_payload[ 'user_state' ] = user_state[ :2 ]
    if user_city and user_city != 'NA':
        caged_donor_payload[ 'user_city' ] = user_city
    if user_zipcode and user_zipcode != 'NA':
        caged_donor_payload[ 'user_zipcode' ] = user_zipcode[ :5 ]

    caged_donor_schema = from_json( CagedDonorSchema(), caged_donor_payload )
    caged_donor_model = caged_donor_schema.data
    return caged_donor_model
