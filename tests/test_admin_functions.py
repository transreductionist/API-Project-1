"""Module to ensure administrative functions, e.g. recording a bounced check, are doing what they should."""
import unittest
from decimal import Decimal

import mock

import tests.helpers.mock_braintree_objects  # pylint: disable=C0412
from application.app import create_app
from application.controllers.admin import admin_correct_gift
from application.controllers.admin import admin_record_bounced_check
from application.controllers.admin import admin_refund_transaction
from application.controllers.admin import admin_void_transaction
from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from application.models.gift import GiftModel
from application.models.transaction import TransactionModel
from application.schemas.agent import AgentSchema
from application.schemas.gift import GiftSchema
from application.schemas.transaction import TransactionSchema
from tests.helpers.create_method_used import create_method_used
from tests.helpers.default_dictionaries import get_agent_dict
from tests.helpers.default_dictionaries import get_gift_dict
from tests.helpers.default_dictionaries import get_transaction_dict
from tests.helpers.manage_ultsys_user_database import create_ultsys_users
from tests.helpers.mock_ultsys_functions import get_ultsys_user


class AdminFunctionsTestCase( unittest.TestCase ):
    """This test suite is designed to verify the administrative functions for refunding and reallocating gifts.

    One important aspect of the tests is that they are designed to validate the referential integrity of the models
    and database when a donation is updated.

    python -m unittest discover -v
    python -m unittest -v tests.test_admin_functions.AdminFunctionsTestCase
    python -m unittest -v tests.test_admin_functions.AdminFunctionsTestCase.test_admin_record_bounced_check
    """

    def setUp( self ):
        self.app = create_app( 'TEST' )
        self.app.testing = True
        self.test_client = self.app.test_client()

        self.parameters = {
            'gift_amount_refund': Decimal( '1.00' ),
            'gift_amount_reallocate': Decimal( '25.00' ),
            'gift_amount_bounced': Decimal( '0.00' ),
            'transaction_type_void': 'Void',
            'transaction_type_bounced': 'Bounced',
            'transaction_type_refund': 'Refund',
            'transaction_type_correction': 'Correction'
        }

        with self.app.app_context():
            database.reflect()
            database.drop_all()
            database.create_all()

            # Create some ultsys user data for the Ultsys endpoints wrapped in functions for mocking.
            create_ultsys_users()

            database.session.add_all( create_method_used() )
            database.session.commit()

    def tearDown( self ):
        with self.app.app_context():
            database.session.commit()
            database.session.close()

    def test_admin_record_bounced_check( self ):
        """Test for recording a bounced check."""

        with self.app.app_context():
            # Create 2 gifts: one for the transaction that needs to record bounced check, the other to query against.

            # Create the bank and sourced by agents for recording a check.
            agent_dict = get_agent_dict(
                {
                    'name': 'Fidelity Bank',
                    'type': 'Organization'
                }
            )
            bank_agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( bank_agent_model.data )
            database.session.flush()

            agent_user_id = 3255162
            agent_dict = get_agent_dict(
                {
                    'name': 'Aaron Peters',
                    'user_id': agent_user_id,
                    'type': 'Staff Member'
                }
            )
            user_agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( user_agent_model.data )
            database.session.flush()

            # Here is the first gift as check.
            gift_dict = get_gift_dict(
                {
                    'method_used_id': 3,
                    'sourced_from_agent_id': 1,
                    'reference_number': '1201',
                    'customer_id': ''
                }
            )
            gift_model = from_json( GiftSchema(), gift_dict, create=True )
            database.session.add( gift_model.data )
            database.session.flush()
            gift_searchable_id = gift_model.data.searchable_id

            # Create the 2nd gift as check.
            gift_dict = get_gift_dict(
                {
                    'method_used_id': 3,
                    'sourced_from_agent_id': 1
                }
            )
            gift_model = from_json( GiftSchema(), gift_dict, create=True )
            database.session.add( gift_model.data )
            database.session.flush()

            # Create 2 transactions on the first gift for the check.
            transaction_dict = get_transaction_dict(
                {
                    'gift_id': 1,
                    'enacted_by_agent_id': 1,
                    'type': 'Gift',
                    'gross_gift_amount': Decimal( '25.00' ),
                    'reference_number': '1201'
                }
            )
            transaction_model = from_json( TransactionSchema(), transaction_dict, create=True )
            database.session.add( transaction_model.data )

            transaction_dict = get_transaction_dict(
                {
                    'gift_id': 1,
                    'enacted_by_agent_id': 2,
                    'type': 'Deposit to Bank',
                    'gross_gift_amount': Decimal( '25.00' ),
                    'reference_number': '<bank-deposit-number>'
                }
            )
            transaction_model = from_json( TransactionSchema(), transaction_dict, create=True )
            database.session.add( transaction_model.data )

            # Put a transaction on the second gift.
            transaction_dict = get_transaction_dict(
                {
                    'gift_id': 2,
                    'enacted_by_agent_id': 1,
                    'type': 'Refund',
                    'gross_gift_amount': Decimal( '25.00' )
                }
            )
            transaction_model = from_json( TransactionSchema(), transaction_dict, create=True )
            database.session.add( transaction_model.data )

            database.session.flush()
            database.session.commit()

            # Call the function to test.
            # Needs the JWT Ultsys agent user ID because calling function directly ( not through resource ).
            payload = {
                'gift_searchable_id': gift_searchable_id,
                'reference_number': '1201',
                'transaction_notes': '',
                'gross_gift_amount': '0.00',
                'user_id': 3255162
            }

            # Calling the function for recording the bounced check directly and bypassing JWT is resource.
            record_bounced_check = admin_record_bounced_check( payload )

            transaction_bounced_check = TransactionModel.query\
                .filter_by( type=self.parameters[ 'transaction_type_bounced' ] ).one_or_none()

            self.assertEqual( record_bounced_check, True )
            self.assertEqual( transaction_bounced_check.enacted_by_agent_id, 2 )
            self.assertEqual( transaction_bounced_check.type, self.parameters[ 'transaction_type_bounced' ] )
            self.assertEqual( transaction_bounced_check.gross_gift_amount, self.parameters[ 'gift_amount_bounced' ] )

    @mock.patch(
        'braintree.Transaction.find',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.TRANSACTION_FIND_SETTLED )
    )
    @mock.patch(
        'braintree.Transaction.refund',
        staticmethod( lambda x, y: tests.helpers.mock_braintree_objects.MockObjects.TRANSACTION_REFUND_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Transaction.Status.Settled',
        staticmethod( tests.helpers.mock_braintree_objects.MockObjects.TRANSACTION_STATUS_SETTLED )
    )
    @mock.patch(
        'braintree.Transaction.Status.Settling',
        staticmethod( tests.helpers.mock_braintree_objects.MockObjects.TRANSACTION_STATUS_SETTLING )
    )
    @mock.patch( 'application.helpers.general_helper_functions.get_ultsys_user', side_effect=get_ultsys_user )
    def test_admin_refund_transaction( self, get_ultsys_user_function  ):   # pylint: disable=unused-argument
        """Test for creating a refund mocking Braintree's responses."""

        with self.app.app_context():
            # Create the transaction to partially refund.

            gift_dict = get_gift_dict(
                {
                    'user_id': '5',
                    'customer_id': 'braintree_customer_id',
                    'recurring_subscription_id': 'subscription_id'
                }
            )
            gift_model = from_json( GiftSchema(), gift_dict, create=True )
            database.session.add( gift_model.data )
            database.session.commit()

            gift_id = gift_model.data.id
            transaction_dict = get_transaction_dict( { 'gift_id': gift_id } )
            transaction_model = from_json( TransactionSchema(), transaction_dict, create=True )
            database.session.add( transaction_model.data )

            # Create the sourced by agent who refunds the transaction.
            agent_dict = get_agent_dict({})
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )

            # Create the enacted by agent who does the refund.
            agent_user_id = '3255162'
            agent_dict = get_agent_dict(
                {
                    'name': 'Aaron Peters',
                    'user_id': agent_user_id,
                    'type': 'Staff Member'
                }
            )
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )

            # Set the database.
            database.session.commit()

            # Call function to tests.
            # The function requires the JWT claim from the ontroller and that is included here in the payload.
            payload = {
                'transaction_id': 1,
                'amount': self.parameters[ 'gift_amount_refund' ],
                'user_id': agent_user_id,
                'transaction_notes': 'Transaction notes.'
            }

            # Calling the function for a refund directly and bypassing JWT is resource.
            refund_result = admin_refund_transaction( payload )

            # The transaction to refund was separately created and has ID equalt 1.
            # The refund is its own transaction and will have ID equal to 2.
            transaction_refund = TransactionModel.query.filter_by( id=2 ).one_or_none()
            self.assertEqual( refund_result, True )
            self.assertEqual( transaction_refund.id, 2 )
            self.assertEqual( transaction_refund.gift_id, gift_id )
            self.assertEqual( transaction_refund.enacted_by_agent_id, 2 )
            self.assertEqual( transaction_refund.type, self.parameters[ 'transaction_type_refund' ] )

            current_gross_gift_amount = \
                Decimal( transaction_dict[ 'gross_gift_amount' ] ) - self.parameters[ 'gift_amount_refund' ]
            self.assertEqual( transaction_refund.gross_gift_amount, current_gross_gift_amount )

    @mock.patch(
        'braintree.Customer.find',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.CUSTOMER_FIND_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Subscription.find',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.SUBSCRIPTION_FIND_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Subscription.update',
        staticmethod( lambda x, y: tests.helpers.mock_braintree_objects.MockObjects.SUBSCRIPTION_UPDATE_SUCCESSFUL )
    )
    def test_braintree_reallocate_gift( self ):
        """Test for reallocating a gift mocking Braintree's responses."""

        with self.app.app_context():
            # Create the transaction to partially refund.

            gift_dict = get_gift_dict(
                {
                    'user_id': '5',
                    'customer_id': 'braintree_customer_id',
                    'recurring_subscription_id': 'subscription_id'
                }
            )
            gift_model = from_json( GiftSchema(), gift_dict, create=True )
            database.session.add( gift_model.data )
            database.session.commit()

            gift_id = gift_model.data.id
            transaction_dict = get_transaction_dict( { 'gift_id': gift_id } )
            transaction_model = from_json( TransactionSchema(), transaction_dict, create=True )
            database.session.add( transaction_model.data )

            # Create the agent who does the refund.
            agent_user_id = '3255162'
            agent_dict = get_agent_dict(
                {
                    'name': 'Aaron Peters',
                    'user_id': agent_user_id,
                    'type': 'Staff Member'
                }
            )
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )

            database.session.commit()

            # Call the function to tests.
            payload = {
                "gift": {
                    "reallocate_to": "NERF"
                },
                "transaction": {
                    "gift_searchable_id": gift_model.data.searchable_id,
                    "gross_gift_amount": self.parameters[ 'gift_amount_reallocate' ],
                    "notes": "An online donation to test receipt sent email."
                },
                "user": {
                    "user_id": None
                },
                "agent_ultsys_id": 322156
            }

            # Calling the function for reallocating a gift directly and bypassing JWT is resource.
            reallocate_result = admin_reallocate_gift( payload )

            gift_reallocate = GiftModel.query.filter_by( id=gift_id ).one_or_none()
            transaction_reallocate = TransactionModel.query.filter_by( id=2 ).one_or_none()

            self.assertEqual( reallocate_result, True )
            self.assertEqual( gift_reallocate.id, gift_id )
            self.assertEqual( gift_reallocate.given_to, payload[ 'gift' ][ 'reallocate_to' ] )
            self.assertEqual( transaction_reallocate.enacted_by_agent_id, 1 )
            self.assertEqual( transaction_reallocate.type, self.parameters[ 'transaction_type_reallocation' ] )
            self.assertEqual( transaction_reallocate.gross_gift_amount, self.parameters[ 'gift_amount_reallocate' ] )

            self.assertEqual( transaction_reallocate.enacted_by_agent_id, 1 )
            self.assertEqual( transaction_reallocate.type, self.parameters[ 'transaction_type_reallocation' ] )
            self.assertEqual( transaction_reallocate.gross_gift_amount, self.parameters[ 'gift_amount_reallocate' ] )

    @mock.patch(
        'braintree.Transaction.find',
        staticmethod(
            lambda x:
            tests.helpers.mock_braintree_objects.MockObjects.TRANSACTION_FIND_SUBMITTED_FOR_SETTLEMENT
        )
    )
    @mock.patch(
        'braintree.Transaction.void',
        staticmethod(
            lambda x:
            tests.helpers.mock_braintree_objects.MockObjects.TRANSACTION_VOID_SUCCESSFUL
        )
    )
    @mock.patch(
        'braintree.Transaction.Status.SubmittedForSettlement',
        staticmethod( tests.helpers.mock_braintree_objects.MockObjects.TRANSACTION_STATUS_SUBMITTED_FOR_SETTLEMENT )
    )
    def test_braintree_void_transaction( self ):
        """Test for voiding a transaction mocking Braintree's response."""

        with self.app.app_context():
            # Create the transaction to void.
            gift_dict = get_gift_dict(
                {
                    'user_id': '5',
                    'customer_id': 'braintree_customer_id',
                    'recurring_subscription_id': 'subscription_id'
                }
            )
            gift_model = from_json( GiftSchema(), gift_dict, create=True )
            database.session.add( gift_model.data )
            database.session.commit()

            gift_id = gift_model.data.id
            transaction_dict = get_transaction_dict( { 'gift_id': gift_id } )
            transaction_model = from_json( TransactionSchema(), transaction_dict, create=True )
            database.session.add( transaction_model.data )

            # Create the sourced by agent who voids the transaction.
            agent_dict = get_agent_dict({})
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )

            # Create the enacted by agent who voids the transaction.
            agent_user_id = '3255162'
            agent_dict = get_agent_dict(
                {
                    'name': 'Aaron Peters',
                    'user_id': agent_user_id,
                    'type': 'Staff Member'
                }
            )
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )

            # Set the database.
            database.session.commit()

            # Call function to tests.
            payload = {
                'transaction_id': 1,
                'user_id': agent_user_id,
                'transaction_notes': 'Transaction notes.'
            }

            # Calling the function to void a transaction directly and bypassing JWT is resource.
            void_result = admin_void_transaction( payload )

            # The transaction to void was separately created and has ID equal to 1.
            # The voided is its own transaction and will have ID equal to 2 attached to gift 1.
            transaction_void = TransactionModel.query.filter_by( id=2 ).one_or_none()

            self.assertEqual( void_result, True )
            self.assertEqual( transaction_void.id, 2 )
            self.assertEqual( transaction_void.gift_id, gift_id )
            self.assertEqual( transaction_void.enacted_by_agent_id, 2 )
            self.assertEqual( transaction_void.type, self.parameters[ 'transaction_type_void' ] )
