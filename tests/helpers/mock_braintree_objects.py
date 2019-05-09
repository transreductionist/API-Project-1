"""These are objects to mock Braintree API calls in the unit tests."""
import copy
import datetime
from decimal import Decimal

import mock
# pylint: disable=too-few-public-methods
# pylint: disable=cyclic-import


class MockObjects:
    """The Braintree objects to be mocked."""

    def __init__( self ):
        pass

    TRANSACTION_SUCCESSFUL = mock.Mock(
        id='braintree_reference_number',
        type='sale',
        amount=Decimal( 25.00 ),
        status='submitted_for_settlement',
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow(),
        payment_instrument_type='credit_card',
        service_fee_amount=Decimal( 0.00 ),
        refunded_transaction_id=None,
        credit_card_details=mock.Mock(
            token='credit_card_details_token',
            bin='bin',
            last_4='last_four',
            card_type='Visa',
            expiration_date='expiration_date',
            cardholder_name='Joshua Albers',
            customer_location='US',
        ),
        customer_details=mock.Mock(
            id='customer_id',
            first_name='Joshua',
            last_name='Albers',
            email='joshuaalbers@disney.com',
            phone='7348723251'
        ),
        custom_fields=mock.Mock(
            user_address='user_address',
            user_city='user_city',
            user_state='user_state',
            user_zipcode='user_zipcode'
        ),
    )

    CREDIT_CARD = mock.Mock(
        token='credit_card_token'
    )

    CUSTOMER_SUCCESSFUL = mock.Mock(
        id='customer_id',
        first_name='Joshua',
        last_name='Albers',
        custom_fields=mock.Mock(
            user_address='user_address',
            user_city='user_city',
            user_state='user_state',
            user_zipcode='user_zipcode'
        ),
        email='joshuaalbers@disney.com',
        phone='7348723251',
        payment_methods=[ CREDIT_CARD ]
    )

    CUSTOMER_SUCCESSFUL_NEW_BILLING_INFORMATION = mock.Mock(
        id='customer_id',
        first_name='Joshua',
        last_name='Albers',
        custom_fields=mock.Mock(
            user_address='user_address',
            user_city='user_city',
            user_state='user_state',
            user_zipcode='user_zipcode'
        ),
        email='joshuaalbers@disney.com',
        phone='7348723251',
        payment_methods=[ CREDIT_CARD ],
        credit_card=mock.Mock(
            billing_address=mock.Mock(
                first_name='Joshua',
                last_name='Albers',
                street_address='126 Jackson Street',
                region='Farmington Hills',
                locality='MI',
                postal_code='48336'
            )
        )
    )

    SUBSCRIPTION_SUCCESSFUL = mock.Mock(
        id='subscription_id',
        transactions=[ TRANSACTION_SUCCESSFUL ]
    )

    PAYMENT_METHOD_SUCCESSFUL = mock.Mock(
        token='payment_method_token'
    )

    TRANSACTION_STATUS_SETTLED = 'settled'
    TRANSACTION_STATUS_SETTLING = 'settling'
    TRANSACTION_STATUS_SUBMITTED_FOR_SETTLEMENT = 'submitted_for_settlement'


MockObjects.TRANSACTION_FIND_SUCCESSFUL = mock.Mock( transaction=MockObjects.TRANSACTION_SUCCESSFUL )

MockObjects.TRANSACTION_FIND_SETTLED = copy.copy( MockObjects.TRANSACTION_SUCCESSFUL )
MockObjects.TRANSACTION_FIND_SETTLED.status = 'settled'

MockObjects.TRANSACTION_LARGE_SUCCESSFUL = copy.copy( MockObjects.TRANSACTION_SUCCESSFUL )
MockObjects.TRANSACTION_LARGE_SUCCESSFUL.amount = '1000'

MockObjects.TRANSACTION_FIND_SUBMITTED_FOR_SETTLEMENT = copy.copy( MockObjects.TRANSACTION_SUCCESSFUL )
MockObjects.TRANSACTION_FIND_SUBMITTED_FOR_SETTLEMENT.status = 'submitted_for_settlement'

MockObjects.TRANSACTION_REFUND = copy.copy( MockObjects.TRANSACTION_SUCCESSFUL )
MockObjects.TRANSACTION_REFUND.refunded_transaction_id = 'refund_id'
MockObjects.TRANSACTION_REFUND.amount = Decimal( 1.00 )
MockObjects.TRANSACTION_REFUND_SUCCESSFUL = mock.Mock( transaction=MockObjects.TRANSACTION_REFUND )

MockObjects.TRANSACTION_VOID = copy.copy( MockObjects.TRANSACTION_SUCCESSFUL )
MockObjects.TRANSACTION_VOID.status = 'voided'
MockObjects.TRANSACTION_VOID_SUCCESSFUL = mock.Mock( transaction=MockObjects.TRANSACTION_VOID )

MockObjects.TRANSACTION_SALE_SUCCESSFUL = mock.Mock( transaction=MockObjects.TRANSACTION_SUCCESSFUL )

MockObjects.SUBSCRIPTION_CREATE_SUCCESSFUL = copy.copy( MockObjects.SUBSCRIPTION_SUCCESSFUL )

MockObjects.CUSTOMER_FIND_SUCCESSFUL = MockObjects.CUSTOMER_SUCCESSFUL

MockObjects.CUSTOMER_CREATE_SUCCESSFUL = mock.Mock(
    is_success=True,
    errors=None,
    customer=MockObjects.CUSTOMER_SUCCESSFUL
)

MockObjects.CUSTOMER_UPDATE_SUCCESSFUL = mock.Mock(
    is_success=True,
    errors=None,
    customer=MockObjects.CUSTOMER_SUCCESSFUL_NEW_BILLING_INFORMATION
)

MockObjects.SALE_CREATE_SUCCESSFUL = mock.Mock(
    is_success=True,
    errors=None,
    transaction=MockObjects.TRANSACTION_SUCCESSFUL
)

MockObjects.SALE_CREATE_LARGE_SUCCESSFUL = mock.Mock(
    is_success=True,
    errors=None,
    transaction=MockObjects.TRANSACTION_LARGE_SUCCESSFUL
)

MockObjects.SUBSCRIPTION_CREATE_SUCCESSFUL = mock.Mock(
    is_success=True,
    errors=None,
    subscription=MockObjects.SUBSCRIPTION_SUCCESSFUL
)

MockObjects.SUBSCRIPTION_FIND_SUCCESSFUL = mock.Mock(
    is_success=True,
    errors=None,
    subscription=MockObjects.SUBSCRIPTION_SUCCESSFUL
)

MockObjects.SUBSCRIPTION_UPDATE_SUCCESSFUL = mock.Mock(
    is_success=True,
    errors=None,
    subscription=MockObjects.SUBSCRIPTION_SUCCESSFUL
)

MockObjects.PAYMENT_METHOD_CREATE_SUCCESSFUL = mock.Mock(
    is_success=True,
    errors=None,
    payment_method=MockObjects.PAYMENT_METHOD_SUCCESSFUL
)


def mock_init_braintree_gateway( current_app ):  # pylint: disable=unused-argument
    """This is the function that mocks the init_braintree_gateway function.

    :param current_app: The current_app ( appears in the mocked function init_braintree_gateway() )
    :return:
    """
    class Transaction:
        """The part of the Braintree sale ( Transaction ) object that we want to mock."""

        def __init__( self ):
            self.transaction = mock.Mock(
                id='braintree_reference_number',
                amount=Decimal( 25.00 ),
                service_fee_amount=Decimal( 0.00 ),
                customer_details=mock.Mock(
                    id='customer_id',
                    first_name='Joshua',
                    last_name='Albers',
                    custom_fields=mock.Mock(
                        user_address='user_address',
                        user_city='user_city',
                        user_state='user_state',
                        user_zipcode='user_zipcode'
                    ),
                    email='joshuaalbers@disney.com',
                    phone='7348723251'
                )
            )

        def find( self, braintree_id ):  # pylint: disable=unused-argument
            """Mocks the transaction.find() function.

            :param braintree_id: The Braintree transaction ID.
            :return: A mocked transaction.find() object.
            """

            return self.transaction

    class Gateway( Transaction ):
        """The Gateway object ( Braintree gateway instance API versus class API )"""

        def __init__( self ):
            super().__init__()
            self.transaction = Transaction()

    return Gateway()


def mock_init_braintree_credentials( current_app ):  # pylint: disable=unused-argument
    """This is the function that mocks the init_braintree_credentials function.

    :param current_app: The current_app
    :return:
    """

    return


def mock_generate_braintree_token():
    """Will mock getting a Braintree token for a transaction.
    :return: Braintree generated token.
    """

    return 'braintree_token'
