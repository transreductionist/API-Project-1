"""The following script will aid in the management of Braintree transactions.
Currently, there is a function that queries the database for all transactions, and then ensures that these are in the
status of 'settled'. The 'settled' status is needed for such operations as refunding a transaction. Other functions
can be added as needed. To run a function navigate to the project root and, for example, on the command line type:

python -c "import scripts.manage_braintree_transactions;scripts.manage_braintree_transactions.manage_sales()"
python -c "import scripts.manage_braintree_transactions;
    scripts.manage_braintree_transactions.create_database_transactions()"
"""
import uuid
from datetime import datetime
from decimal import Decimal
from time import sleep

import braintree

from application.app import create_app
from application.flask_essentials import database
from application.helpers.braintree_api import init_braintree_credentials
from application.helpers.model_serialization import from_json
from application.models.agent import AgentModel
from application.models.transaction import TransactionModel
from application.schemas.gift import GiftSchema
from application.schemas.transaction import TransactionSchema

app = create_app( 'DEV' )  # pylint: disable=C0103

init_braintree_credentials( app )

MODEL_DATE_STRING_FORMAT = '%Y-%m-%d %H:%M:%S'
BRAINTREE_DATE_STRING_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

DEFAULT_DATE_IN_UTC = datetime.fromtimestamp( 0 ).strftime( MODEL_DATE_STRING_FORMAT )

VALID_CARD_NUMBER = '4111111111111111'
DISPUTE_CARD_NUMBER = '4023898493988028'
AMOUNT_VALID = '20.00'
AMOUNT_GATEWAY_REJECTED = '5001.00'
AMOUNT_PROCESSOR_DECLINED = '2000.00'

MERCHANT_ACCOUNT_ID = {
    'NERF': 'numbersusa',
    'ACTION': 'numbersusa_action'
}

MERCHANT_ID_GIVEN_TO = {
    'numbersusa': 'NERF',
    'numbersusa_action': 'ACTION'
}

# Get the Agent ID from the model for type Automated:
with app.app_context():
    AGENT_MODEL = AgentModel.get_agent( 'Automated', 'type', 'Automated' )  # pylint: disable=invalid-name
    AGENT_ID = str( AGENT_MODEL.id )


def manage_sales():
    """A workbench that you can use to create and manipulate Braintree sales."""

    print( '\n\n# ******************** MANAGE SALES ******************** #' )
    print( '            datetime.now()   : {}\n'.format( datetime.now().strftime( MODEL_DATE_STRING_FORMAT ) ) )
    print( '            datetime.utcnow(): {}\n'.format( datetime.utcnow().strftime( MODEL_DATE_STRING_FORMAT ) ) )

    braintree_id = '5e4vmzcx'
    secs = 2
    set_status_settled_by_id( braintree_id, secs )


def create_valid_refund_with_void():
    """Create sale, settle it, do a partial refund, and void the refund."""

    merchant_account_id = MERCHANT_ACCOUNT_ID[ 'ACTION' ]
    customer = customer_dict( 'Bertrand', 'Russel', '7032990001', VALID_CARD_NUMBER )
    sale = create_sale( customer, AMOUNT_VALID, merchant_account_id, 'Valid', 5 )

    gift_dict = {
        'id': None,
        'searchable_id': uuid.uuid4(),
        'user_id': 9999,
        'method_used': 'Web Form Credit Card',
        'sourced_from_agent_id': AGENT_ID,
        'given_to': MERCHANT_ID_GIVEN_TO[ merchant_account_id ],
        'recurring_subscription_id': None
    }
    gift_model = build_gift( gift_dict )

    transaction_dict = {
        'gift_id': gift_model.id,
        'date_in_utc': sale.created_at.strftime( MODEL_DATE_STRING_FORMAT ),
        'enacted_by_agent_id': AGENT_ID,
        'type': 'Gift',
        'status': 'Completed',
        'reference_number': sale.id,
        'gross_gift_amount': sale.amount,
        'fee': sale.service_fee_amount if sale.service_fee_amount else Decimal( 0 ),
        'notes': 'Created in manage_sales() as initial sale.'
    }
    build_transaction( transaction_dict )

    set_status_settled_by_id( sale.id, 5 )
    refund = create_refund( sale.id, '0.01', 5 )
    void_sale( refund.id, 5 )

    # Create a valid sale and void.
    sale = create_sale( customer, AMOUNT_VALID, merchant_account_id, 'Valid', 60 )

    gift_dict = {
        'id': None,
        'searchable_id': uuid.uuid4(),
        'user_id': 9999,
        'method_used': 'Web Form Credit Card',
        'sourced_from_agent_id': AGENT_ID,
        'given_to': MERCHANT_ID_GIVEN_TO[ merchant_account_id ],
        'recurring_subscription_id': None
    }
    gift_model = build_gift( gift_dict )

    transaction_dict = {
        'gift_id': gift_model.id,
        'date_in_utc': sale.created_at.strftime( MODEL_DATE_STRING_FORMAT ),
        'enacted_by_agent_id': AGENT_ID,
        'type': 'Gift',
        'status': 'Completed',
        'reference_number': sale.id,
        'gross_gift_amount': sale.amount,
        'fee': sale.service_fee_amount if sale.service_fee_amount else Decimal( 0 ),
        'notes': 'Created in manage_sales() as initial sale.'
    }
    build_transaction( transaction_dict )
    void_sale( sale.id, 5 )


def create_sale_with_dispute():
    """Create sale, settle it, do a partial refund, and void the refund."""

    merchant_account_id = MERCHANT_ACCOUNT_ID[ 'ACTION' ]
    customer = customer_dict( 'Bertrand', 'Russel', '7032990001', DISPUTE_CARD_NUMBER )
    sale = create_sale( customer, AMOUNT_VALID, merchant_account_id, 'Dispute', 5 )

    gift_dict = {
        'id': None,
        'searchable_id': uuid.uuid4(),
        'user_id': 9999,
        'method_used': 'Web Form Credit Card',
        'sourced_from_agent_id': AGENT_ID,
        'given_to': MERCHANT_ID_GIVEN_TO[ merchant_account_id ],
        'recurring_subscription_id': None
    }
    gift_model = build_gift( gift_dict )

    transaction_dict = {
        'gift_id': gift_model.id,
        'date_in_utc': sale.created_at.strftime( MODEL_DATE_STRING_FORMAT ),
        'enacted_by_agent_id': AGENT_ID,
        'type': 'Gift',
        'status': 'Completed',
        'reference_number': sale.id,
        'gross_gift_amount': sale.amount,
        'fee': sale.service_fee_amount if sale.service_fee_amount else Decimal( 0 ),
        'notes': 'Created in manage_sales() as initial sale.'
    }
    build_transaction( transaction_dict )


def create_sale( customer, amount, merchant_account_id, sale_type, secs ):
    """Handles creating the customer, getting a token, and making a Braintree sale calling create_braintree_sale.

    :param customer: A Braintree customer with credit card details.
    :param amount: A sale amount.
    :param merchant_account_id: The merchant account ID to make the sale to.
    :param sale_type: The type of sale such as Valid.
    :param secs: Used by sleep() to prevent errors like gateway rejected.
    :return: The transaction for the Braintree sale.
    """

    with app.app_context():
        sleep( secs )
        braintree_customer = create_braintree_customer( customer )
        braintree_customer_id = braintree_customer.customer.id
        payment_method_token = braintree_customer.customer.payment_methods[ 0 ].token
        braintree_sale = create_braintree_sale(
            amount,
            payment_method_token,
            braintree_customer_id,
            merchant_account_id
        )

        print()
        print( '{} {}'.format( customer[ 'first_name' ], customer[ 'last_name' ] ) )
        print( '    type               : {}'.format( sale_type ) )
        print( '    merchant_account_id: {}'.format( braintree_sale.transaction.merchant_account_id ) )
        print( '    id                 : {}'.format( braintree_sale.transaction.id ) )
        print( '    card               : {}'.format( customer[ 'credit_card' ][ 'number' ] ) )
        print( '    amount             : {}'.format( amount ) )
        print()

        return braintree_sale.transaction


def create_braintree_customer( customer_json ):
    """Create a Braintree customer in the vault.

    :param customer_json: The customer dictionary.
    :return: Braintree customer
    """

    customer = braintree.Customer.create( customer_json )
    return customer


def create_braintree_sale( amount, payment_method_token, customer_id, merchant_account_id ):
    """Given a customer ID create_braintree_customer() create a Braintree sale.

    :param amount: The amount for the sale.
    :param payment_method_token: A payment method token for the customer.
    :param customer_id: The Braintree vault customer ID.
    :param merchant_account_id: The merchant account to make sale to.
    :return: A Braintree sale.
    """

    sale = braintree.Transaction.sale(
        {
            'amount': amount,
            'payment_method_token': payment_method_token,
            'customer_id': customer_id,
            'merchant_account_id': merchant_account_id,
            'options': {
                'submit_for_settlement': True,
                'store_in_vault_on_success': True
            }
        }
    )
    return sale


def create_refund( braintree_id, amount, secs ):
    """Creates a Braintree refund for the amount provided against the sale identified by the braintree_id.

    :param braintree_id: The Braintree sale ID to partially/fully refund.
    :param amount: The partial/full amount to refund.
    :param secs: Used by sleep() to prevent errors like gateway rejected.
    :return: A Braintree refund transaction.
    """

    sleep( secs )
    refund = braintree.Transaction.refund( braintree_id, amount )

    print()
    print( 'Refund' )
    print( '    Refund ID: {}'.format( refund.transaction.id ) )
    print( '    Parent ID: {}'.format( refund.transaction.refunded_transaction_id ) )
    print()

    return refund.transaction


def void_sale( braintree_id, secs ):
    """Void a Braintree sale ( must be in submitted_for_settlement ).

    :param braintree_id: The Braintree sale ID to void.
    :param secs: Used by sleep() to prevent errors like gateway rejected.
    :return: A Braintree voided transaction.
    """

    sleep( secs )
    void = braintree.Transaction.void( braintree_id )

    print()
    print( 'Void' )
    print( '    Voided ID: {}'.format( void.transaction.id ) )
    print()

    return void.transaction


def set_status_settled():
    """Get all the transactions from the database and set them to settled status."""

    with app.app_context():
        model_transactions = TransactionModel.query.all()

    transaction_ids = []
    for model_transaction in model_transactions:
        braintree_id = model_transaction.reference_number
        transaction = braintree.Transaction.find( braintree_id )
        transaction_ids.append( transaction.id )

        # Ensure in status of settling or settled.
        testing_gateway = braintree.TestingGateway( braintree.Configuration.gateway() )
        testing_gateway.settle_transaction( braintree_id )

    for transaction_id in transaction_ids:
        print( transaction_id )


def set_status_settled_by_id( braintree_id, secs ):
    """Given a Braintree ID set its status to settled.

    Allows it to be refunded.

    :param braintree_id: A Braintree sale ID.
    :param secs: Used by sleep() to prevent errors like gateway rejected.
    :return:
    """

    # Ensure in status of settling or settled.
    sleep( secs )
    testing_gateway = braintree.TestingGateway( braintree.Configuration.gateway() )
    testing_gateway.settle_transaction( braintree_id )

    print()
    print( 'Set status settled' )
    print( '    sales ID: {}'.format( braintree_id ) )
    print()


def customer_dict( first, last, phone, card_number ):
    """Creates a Braintree customer dictionary with credit card details.

    :param first: Customer's first name.
    :param last: Customer's last name.
    :param phone: Custome's phone number.
    :param card_number: Customer's card number ( can be used to create certain types of sales ).
    :return: The customer dictionary.
    """

    customer = {
        'first_name': first,
        'last_name': last,
        "custom_fields": {
            "user_address": '328 Chauncy St',
            "user_city": 'Bensonhurst',
            "user_state": 'NY',
            "user_zipcode": '11214',
        },
        'email': '{}{}@gmail.com'.format( first, last ),
        'phone': phone,
        'payment_method_nonce': 'fake-valid-visa-nonce',
        'credit_card': {
            'billing_address': {
                'first_name': first,
                'last_name': last,
                'street_address': '{} {} Ave'.format( first, last ),
                'region': 'Bensonhurst',
                'locality': 'NY',
                'postal_code': '11214'
            },
            'cardholder_name': '{} {}'.format( first, last ),
            'number': card_number,
            'expiration_month': '10',
            'expiration_year': '2019',
            'cvv': '123'
        }
    }
    return customer


def create_database_transactions():
    """Uses Braintree sales during a specified interval to build the initial gift and transaction in the database.

    Very useful for filling the database and then running the transaction updater for testing. The transactions
    created here will have type 'Gift' and status 'Completed'.
    """

    dates = { 'month_0': 7, 'day_0': 1, 'month_1': 7, 'day_1': 31 }
    date1 = datetime.utcnow().replace(
        month=dates[ 'month_1' ], day=dates[ 'day_1' ], hour=23, minute=59, second=59, microsecond=9999
    )
    date0 = datetime.utcnow().replace(
        month=dates[ 'month_0' ], day=dates[ 'day_0' ], hour=0, minute=0, second=0, microsecond=0
    )
    print( '{} ~ {}'.format( date0.strftime( MODEL_DATE_STRING_FORMAT ), date1.strftime( MODEL_DATE_STRING_FORMAT ) ) )

    with app.app_context():

        date_in_utc = datetime.fromtimestamp( 0 )
        sales_authorized = {}
        search_at( date0, date1, 'authorized_at', sales_authorized )
        for sales_id, sale in sales_authorized.items():  # pylint: disable=unused-variable
            gift_dict = {
                'id': None,
                'searchable_id': uuid.uuid4(),
                'user_id': 999999999,
                'method_used': 'Web Form Credit Card',
                'sourced_from_agent_id': AGENT_ID,
                'given_to': MERCHANT_ID_GIVEN_TO[ sale.merchant_account_id ],
                'recurring_subscription_id': sale.subscription_id
            }
            gift_model = from_json( GiftSchema(), gift_dict )
            database.session.add( gift_model.data )
            database.session.flush()
            database.session.commit()

            for history_item in sale.status_history:
                date_in_utc = datetime.fromtimestamp( 0 )
                if history_item.status == 'authorized':
                    date_in_utc = history_item.timestamp.strftime( MODEL_DATE_STRING_FORMAT )
                    break

            transaction_dict = {
                'gift_id': gift_model.data.id,
                'date_in_utc': date_in_utc,
                'enacted_by_agent_id': AGENT_ID,
                'type': 'Gift',
                'status': 'Completed',
                'reference_number': sale.id,
                'gross_gift_amount': sale.amount,
                'fee': sale.service_fee_amount if sale.service_fee_amount else Decimal( 0 ),
                'notes': 'Automated creation of transaction.'
            }

            transaction_model = from_json( TransactionSchema(), transaction_dict )
            database.session.add( transaction_model.data )
            database.session.commit()


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
    for braintree_transaction in braintree.Transaction.search( search_obj_at.between( date0, date1 ) ):
        if braintree_transaction.id not in sales:
            sales[ braintree_transaction.id ] = braintree_transaction


def build_gift( gift_dict ):
    """Given a dictionary for the Gift builds, commits and returns the model.

    Uses flush() so we can get the Gift ID.

    :param gift_dict: The Gift dictionary.
    :return: gift_model.data: The Gift model built from the given dictionary and has the new auto-incremented ID.
    """

    with app.app_context():
        gift_model = from_json( GiftSchema(), gift_dict, create=True )
        database.session.add( gift_model.data )
        database.session.flush()
        database.session.commit()
        print()
        print( 'Build GiftModel' )
        print( '    gift_model.id      : {}'.format( gift_model.data.id ) )
        print( '    gift_model.given_to: {}'.format( gift_model.data.given_to ) )
        print()
        return gift_model.data


def build_transaction( transaction_dict ):
    """Given a transaction dictionary method builds the model.

    :param transaction_dict: The transaction dictionary.
    :return: transaction.model.data: The Transaction model built from the given dictionary.
    """

    with app.app_context():
        transaction_model = from_json( TransactionSchema(), transaction_dict, create=True )
        database.session.add( transaction_model.data )
        database.session.commit()
        print()
        print( ' Build TransactionModel' )
        print( '    transaction_model.id         : {}'.format( transaction_model.data.id ) )
        print( '    transaction_model.date_in_utc: {}'.format( transaction_model.data.date_in_utc ) )
        print( '    transaction_model.type       : {}'.format( transaction_model.data.type ) )
        print( '    transaction_model.status     : {}'.format( transaction_model.data.status ) )
        print()
        return transaction_model.data
