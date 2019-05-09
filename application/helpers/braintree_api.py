"""A module to support Braintree API operations."""
import json
from decimal import Decimal

import braintree
from flask import current_app

from application.exceptions.exception_braintree import BraintreeAttributeError
from application.exceptions.exception_braintree import BraintreeNotFoundError
from application.exceptions.exception_braintree import BraintreeNotInSettlingOrSettledError
from application.exceptions.exception_braintree import BraintreeNotInSubmittedForSettlementError
from application.exceptions.exception_braintree import BraintreeNotIsSuccessError
from application.exceptions.exception_braintree import BraintreeRefundWithNegativeAmountError
from application.models.agent import AgentModel
from application.models.method_used import MethodUsedModel
from application.schemas.braintree_sale import BraintreeSaleSchema
# pylint: disable=bare-except
# flake8: noqa:E722


def make_braintree_refund( braintree_id, amount, current_balance ):
    """Use the payload to build a Braintree Transaction.refund(). The sale has to be in a status of settling or
    settled.

    :param str braintree_id: The Braintree transaction ID to refund.
    :param str amount: The amount to refund and must be less than current balance.
    :param str current_balance: The current balance on the account.
    :return: Returns Braintree refund transaction.
    :raises BraintreeNotFoundError: Braintree object was not found.
    :raises BraintreeNotInSettlingOrSettledError: The transaction status is not in proper status.
    :raises BraintreeRefundWithNegativeAmountError: Can't refund a negative amount.
    """

    # Get Braintree transaction status.
    transaction = get_braintree_transaction( braintree_id )

    # Ensure transaction is in status of settling or settled.
    if transaction.status in [ braintree.Transaction.Status.Settled, braintree.Transaction.Status.Settling ]:
        # Refund braintree transaction: check to ensure amount is less than current balance.
        if current_balance - Decimal( amount ) >= 0:
            result_refund = create_braintree_refund( transaction.id, amount )
            return result_refund
        raise BraintreeRefundWithNegativeAmountError

    raise BraintreeNotInSettlingOrSettledError


def make_braintree_void( braintree_id ):
    """Use the payload to void a Braintree Transaction.sale(). The sale has to be in a status of submitted for
    settlement.

    :param str braintree_id: The Braintree transaction ID to void.
    :return: Returns Braintree voided transaction.
    :raises SQLAlchemyError: If the agent ID cannot be found SQLAlchemy raises an exception.
    """

    # Get Braintree transaction status.
    transaction = get_braintree_transaction( braintree_id )

    # Ensure transaction is in status of submitted for settlement.
    if transaction.status == braintree.Transaction.Status.SubmittedForSettlement:
        # Void braintree transaction.
        result_void = braintree.Transaction.void( transaction.id )
        if result_void.is_success:
            return result_void
        errors = handle_braintree_errors( result_void )
        raise BraintreeNotIsSuccessError( errors )
    raise BraintreeNotInSubmittedForSettlementError


def make_braintree_sale( payload, app ):
    """Use the form data, front-end payload, to build a Braintree Transaction.sale().

    The payload is: payload = { 'user': user, 'transaction': transaction, and 'gift': gift }

    These will be used to build the 3 models required by the transaction: UserModel, GiftModel, and TransactionModel.

    The process includes:

        1. Categorize donor: new, cage, exists, or caged.
        2. Find, and if required create a Braintree customer ( customer_id ).
        3. If a subscription is requested create one ( recurring_subscription_id ).
        4. Create the Braintree sale ( Braintree transaction ID among other things )

    With the categorization and transaction processed the initialized dictionaries are updated. Any errors that
    may arise during Braintree transactions are handled. When completed, the model dictionaries are returned to the
    calling function. If there are any errors those are raised.

    :param dict payload: A dictionary with form data from the front-end. ( See controller for payload content. )
    :param app: The current app.
    :return: Returns a dictionary with model data.
    :raises SQLAlchemyORMNoResultFoundError: The ORM didn't find the table row.
    """

    merchant_account_id = {
        'NERF': app.config[ 'NUMBERSUSA' ],
        'ACTION': app.config[ 'NUMBERSUSA_ACTION' ]
    }

    # Attach payment method nonce to user for customer and sale create.
    payload[ 'user' ][ 'payment_method_nonce' ] = payload[ 'payment_method_nonce' ]

    # We don't want to do caging up front because it takes too long. Move to end of the sale in controller.
    # Assign a category: 'queued' and a user ID of -2 ( -1 is used for caged )
    payload[ 'user' ][ 'category' ] = 'queued'
    payload[ 'gift' ][ 'user_id' ] = -2

    # Setting the user to queued handle the creation of the Braintree customer, for example:
    #     1. If they are a new donor the Braintree customer has to be created.
    #     2. If they exist they may or may not have a Braintree customer ID.

    payload[ 'user' ][ 'customer_id' ] = ''

    # The parameter recurring_subscription is a Boolean.
    recurring_subscription = payload[ 'recurring_subscription' ]
    if isinstance( payload[ 'recurring_subscription' ], str ):
        recurring_subscription = json.loads( payload[ 'recurring_subscription' ] )

    if recurring_subscription:

        # Create the customer and pull the payment method token.
        payment_method_token = get_payment_method_token( payload )

        # Use this current payment method token to create the subscription.
        result_subscription = create_braintree_subscription(
            payment_method_token,
            merchant_account_id[ payload[ 'gift' ][ 'given_to' ] ],
            payload[ 'transaction' ][ 'gross_gift_amount' ],
            merchant_account_id[ payload[ 'gift' ][ 'given_to' ] ]
        )
        payload[ 'gift' ][ 'recurring_subscription_id' ] = result_subscription.subscription.id
        braintree_sale = result_subscription.subscription.transactions[ 0 ]
    else:
        # Create Transaction.sale() on Braintree.

        # Create the customer and pull the payment method token.
        payment_method_token = get_payment_method_token( payload )

        result_sale = create_braintree_sale(
            payment_method_token,
            payload[ 'user' ],
            payload[ 'transaction' ][ 'gross_gift_amount' ],
            merchant_account_id[ payload[ 'gift' ][ 'given_to' ] ]
        )

        # Finish creating dictionaries for deserialization later.
        braintree_sale = result_sale.transaction

    # Use BraintreeSaleSchema to populate gift and transaction dictionaries.
    braintree_schema = BraintreeSaleSchema()
    braintree_schema.context = {
        'gift': payload[ 'gift' ],
        'transaction': payload[ 'transaction' ]
    }
    braintree_sale = braintree_schema.dump( braintree_sale )
    gift = braintree_sale.data[ 'gift' ]
    transaction = braintree_sale.data[ 'transaction' ]

    # Get the sourced from agent ID and if it doesn't exist handle.
    if gift[ 'method_used' ] == 'Admin-Entered Credit Card':
        sourced_from_agent = AgentModel.get_agent( 'Staff Member', 'user_id', payload[ 'sourced_from_agent_user_id' ] )
        gift[ 'sourced_from_agent_id' ] = sourced_from_agent.id

    # Get the enacted by agent ID and if it doesn't exist handle.
    enacted_by_agent = AgentModel.get_agent( 'Organization', 'name', 'Braintree' )
    transaction[ 'enacted_by_agent_id' ] = enacted_by_agent.id

    # On success of sale return the model dictionaries.
    return { 'transactions': [ transaction ], 'gift': gift, 'user': payload[ 'user' ] }


def get_payment_method_token( payload ):
    """Create a payment method token and return.

    :param payload: The payload includes the user, gift, and transaction.
    :return:
    """
    method_used = MethodUsedModel.get_method_used( 'name', payload[ 'gift' ][ 'method_used' ] )
    braintree_customer = create_braintree_customer( payload[ 'user' ], method_used.billing_address_required  )
    payload[ 'user' ][ 'customer_id' ] = braintree_customer.id
    # This was newly created and the only payment method associated with the customer.
    return braintree_customer.payment_methods[ 0 ].token


def create_braintree_customer( user, billing_address_required ):
    """Given a dictionary representing the donor the function creates a Braintree customer and returns ID.

    :param dict user: Dictionary that has all the UserModel fields on it.
    :param billing_address_required: 0, or 1 depending on whether billing address required.
    :return: Customer ID if successful or None if not.
    :raises BraintreeIsNotSuccess: The Braintree operation was unsuccessful.
    """

    # Separate addresses for customer and billing.
    user_address = user[ 'user_address' ]
    customer = {
        'first_name': user_address[ 'user_first_name' ],
        'last_name': user_address[ 'user_last_name' ],
        "custom_fields": {
            "user_address": user_address[ 'user_address' ],
            "user_city": user_address[ 'user_city' ],
            "user_state": user_address[ 'user_state' ],
            "user_zipcode": user_address[ 'user_zipcode' ],
        },
        'email': user_address[ 'user_email_address' ],
        'phone': user_address[ 'user_phone_number' ],
        'payment_method_nonce': user[ 'payment_method_nonce' ],
    }
    if billing_address_required:
        # If billing address is required, but empty, then user address is the billing address.
        if 'billing_address' in user and user[ 'billing_address' ]:
            billing_address = user[ 'billing_address' ]
        else:
            billing_address = {}
            for address_key, address_value in user[ 'user_address' ].items():
                billing_address[ address_key.replace( 'user_', 'billing_' ) ] = address_value

        customer[ 'credit_card' ] = {
            'options': { 'verify_card': True },
            'billing_address': {
                'first_name': billing_address[ 'billing_first_name' ],
                'last_name': billing_address[ 'billing_last_name' ],
                'street_address': billing_address[ 'billing_address' ],
                'region': billing_address[ 'billing_city' ],
                'locality': billing_address[ 'billing_state' ],
                'postal_code': billing_address[ 'billing_zipcode' ]
            }
        }

    result_customer = braintree.Customer.create( customer )

    if result_customer.is_success:
        return result_customer.customer
    errors = handle_braintree_errors( result_customer )
    raise BraintreeNotIsSuccessError( errors )


def create_braintree_sale( payment_method_token, user, gross_gift_amount, merchant_account_id ):
    """Given a payment method token, gift amount, and customer ID create a Braintree sale.

    :param str payment_method_nonce: The payment method nonce.
    :param dict user: The user along with  customer_id.
    :param str gross_gift_amount: The amount to donate.
    :param str merchant_account_id: The merchant account ID.
    :return: A Braintree Transaction.sale() is returned.
    :raises BraintreeIsNotSuccess: Braintree operation was unsuccessful.
    """

    result_sale = braintree.Transaction.sale(
        {
            'amount': gross_gift_amount,
            'payment_method_token': payment_method_token,
            'customer_id': user[ 'customer_id' ],
            'merchant_account_id': merchant_account_id,
            'options': {
                'submit_for_settlement': True,
                'store_in_vault_on_success': True
            }
        }
    )

    if result_sale.is_success:
        return result_sale
    errors = handle_braintree_errors( result_sale )
    raise BraintreeNotIsSuccessError( errors )


def create_braintree_subscription( payment_method_token, plan_id, gross_gift_amount, merchant_account_id ):
    """Given a payment method token, plan ID, and gift amount create a Braintree subscription.
    :param str payment_method_token: Comes from the Braintree customer.
    :param str plan_id: What subscription plan ( given_to ).
    :param str gross_gift_amount: The amount to donate.
    :param str merchant_account_id: The merchant account ID.
    :return: A Braintree Subscription.create().
    :raises BraintreeIsNotSuccess: Braintree operation was unsuccessful.
    """

    result_subscription = braintree.Subscription.create(
        {
            'payment_method_token': payment_method_token,
            'plan_id': plan_id,
            'price': gross_gift_amount,
            'merchant_account_id': merchant_account_id,
            'options': { 'start_immediately': True }
        }
    )
    if result_subscription.is_success:
        return result_subscription
    errors = handle_braintree_errors( result_subscription )
    raise BraintreeNotIsSuccessError( errors )


def create_braintree_refund( transaction_id, amount ):
    """Given a transaction ID and amount create a Braintree refund.
    :param str transaction_id: A valid Braintree customer_id.
    :param str amount: The amount to refund.
    :return: A refund result.
    :raises BraintreeNotFoundError: Braintree object was not found.
    """

    try:
        return braintree.Transaction.refund( transaction_id, amount )
    except braintree.exceptions.not_found_error.NotFoundError:
        raise BraintreeNotFoundError()


def get_braintree_transaction( braintree_id ):
    """

    :param braintree_id: Braintree sale ID.
    :return: transaction status.
    """

    try:
        transaction = braintree.Transaction.find( braintree_id )
    except braintree.exceptions.not_found_error.NotFoundError:
        raise BraintreeNotFoundError()

    return transaction


def init_braintree_credentials( app ):
    """Configure the Braintree API."""

    with app.app_context():

        # The default environment is set to the Sandbox.
        merchant_id = app.config[ 'MERCHANT_ID' ]
        public_key = app.config[ 'MERCHANT_PUBLIC_KEY' ]
        private_key = app.config[ 'MERCHANT_PRIVATE_KEY' ]
        if app.config[ 'BRAINTREE_ENVIRONMENT' ] == 'production':
            braintree_environment = braintree.Environment.Production
        else:
            braintree_environment = braintree.Environment.Sandbox

        braintree.Configuration.configure(
            braintree_environment,
            merchant_id=merchant_id,
            public_key=public_key,
            private_key=private_key
        )


def init_braintree_gateway( app ):
    """Configure the Braintree API gateway.

    :param app: The current app.
    :return: Braintree gateway.
    """

    with app.app_context():

        # The default environment is set to the Sandbox.
        merchant_id = app.config[ 'MERCHANT_ID' ]
        public_key = app.config[ 'MERCHANT_PUBLIC_KEY' ]
        private_key = app.config[ 'MERCHANT_PRIVATE_KEY' ]
        braintree_environment = app.config[ 'BRAINTREE_ENVIRONMENT' ]

        if braintree_environment == 'production':
            braintree_environment = braintree.Environment.Production
        else:
            braintree_environment = braintree.Environment.Sandbox

        gateway = braintree.BraintreeGateway(
            braintree.Configuration(
                braintree_environment,
                merchant_id=merchant_id,
                public_key=public_key,
                private_key=private_key
            )
        )

        return gateway


def generate_braintree_token():
    """Will get a Braintree token for a transaction.
    :return: Braintree generated token.
    """

    return braintree.ClientToken.generate()


def handle_braintree_errors( result ):
    """Will handle errors for Braintree API calls.

    :param odj result: Braintree result object, e.g. braintree.Transaction.sale({}).
    :return: Dictionary with information about the error.
    """

    errors = {}

    try:
        # Trap the top level message ( may be duplicated lower down the tree ).
        if result.message:
            errors[ 'message' ] = {
                'code': None,
                'text': result.message
            }

        # Get all the deep errors down the tree:
        if result.errors.deep_errors:
            errors[ 'validation' ] = []
            for error in result.errors.deep_errors:
                errors[ 'validation' ].append(
                    { 'code': error.code, 'text': error.message }
                )

        # Handle AVS errors if there are any:
        response_code = {
            'M': 'Matches',
            'N': 'Does not match',
            'U': 'Not verified',
            'I': 'Not provided',
            'S': 'Issuer does not participate',
            'A': 'Not applicable',
            'B': 'Bypass'
        }

        avs_error = result.credit_card_verification.status == 'gateway_rejected' \
            and result.credit_card_verification.gateway_rejection_reason == 'avs'
        cvv_error = result.credit_card_verification.status == 'gateway_rejected' \
            and result.credit_card_verification.gateway_rejection_reason == 'cvv'
        avs_and_cvv_error = result.credit_card_verification.status == 'gateway_rejected' \
            and result.credit_card_verification.gateway_rejection_reason == 'avs_and_cvv'

        admin = False
        if 'ADMIN' in current_app.config and current_app.config[ 'ADMIN' ]:
            admin = current_app.config[ 'ADMIN' ]

        if ( avs_error or avs_and_cvv_error ) and admin:
            errors[ 'avs' ] = {}
            errors[ 'avs' ][ 'response_code' ] = None
            if result.credit_card_verification.avs_error_response_code:
                errors[ 'avs' ][ 'response_code' ] = result.credit_card_verification.avs_error_response_code
            errors[ 'avs' ][ 'is_zipcode_valid' ] = \
                response_code[ result.credit_card_verification.avs_postal_code_response_code ]
            errors[ 'avs' ][ 'is_street_address_valid' ] = \
                response_code[ result.credit_card_verification.avs_street_address_response_code ]
        elif ( avs_error or avs_and_cvv_error ) and not admin:
            errors[ 'avs' ] = 'Braintree AVS error.'
            errors[ 'cvv' ] = 'Braintree CVV error.'

        if cvv_error and admin:
            errors[ 'cvv' ] = response_code[ result.credit_card_verification.cvv_response_code ]
        elif cvv_error and not admin:
            errors[ 'cvv' ] = 'Braintree CVV error.'

    except AttributeError:
        raise BraintreeAttributeError()

    return { 'errors': errors }
