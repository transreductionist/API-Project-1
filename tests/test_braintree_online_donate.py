"""Tests the online donation process."""
import unittest
import uuid
from decimal import Decimal

import mock

import tests.helpers.mock_braintree_objects  # pylint: disable=ungrouped-imports
from application.app import create_app
from application.controllers.donate import post_donation
from application.flask_essentials import database
from application.helpers.braintree_api import init_braintree_credentials
from application.helpers.model_serialization import from_json
from application.models.caged_donor import CagedDonorModel
from application.models.gift import GiftModel
from application.models.method_used import MethodUsedModel
from application.models.transaction import TransactionModel
from application.schemas.agent import AgentSchema
from application.schemas.caged_donor import CagedDonorSchema
from tests.helpers.create_method_used import create_method_used
from tests.helpers.default_dictionaries import get_agent_dict
from tests.helpers.default_dictionaries import get_caged_donor_dict
from tests.helpers.default_dictionaries import get_donate_dict
from tests.helpers.default_dictionaries import get_new_donor_dict
from tests.helpers.manage_ultsys_user_database import create_ultsys_users
from tests.helpers.mock_redis_queue_functions import mock_caging
from tests.helpers.mock_ultsys_functions import create_user
from tests.helpers.mock_ultsys_functions import get_ultsys_user
from tests.helpers.mock_ultsys_functions import update_ultsys_user
from tests.helpers.ultsys_user_model import UltsysUserModel


class BraintreeOnlineDonateTestCase( unittest.TestCase ):
    """This test suite is designed to verify the online donation process.

    One important aspect of the tests is that they are designed to validate the referential integrity of the models
    and database when a donation is created. A donation will create a transaction, gift, and a donor in the
    database, which refer to one another. The donor may be a new, or existing donor. They may also be a new, or
    existing caged donor.

    python -m unittest discover -v
    python -m unittest -v tests.test_braintree_online_donate.BraintreeOnlineDonateTestCase
    python -m unittest -v tests.test_braintree_online_donate.BraintreeOnlineDonateTestCase.test_donation_new_donor
    """

    def setUp( self ):
        self.app = create_app( 'TEST' )
        self.app.testing = True
        self.test_client = self.app.test_client()

        self.parameters = {
            'reference_number': 'braintree_reference_number',
            'user_exists_id': 5,
            'user_new_id': '67',
            'customer_id': 'customer_id',
            'method_used': 'Web Form Credit Card',
            'given_to': 'NERF',
            'transaction_status': 'Completed',
            'transaction_type': 'Gift',
            'gross_gift_amount': Decimal( 25.00 ),
            'fee': Decimal( 0.00 )
        }

        init_braintree_credentials( self.app )

        with self.app.app_context():
            database.reflect()
            database.drop_all()
            database.create_all()

            # Create some ultsys user data for the Ultsys endpoints wrapped in functions for mocking.
            create_ultsys_users()

            database.session.add_all( create_method_used() )
            database.session.commit()
            self.method_used_id = MethodUsedModel.get_method_used( 'name', self.parameters[ 'method_used' ] ).id

    def tearDown( self ):
        with self.app.app_context():
            database.reflect()
            database.drop_all()
            database.create_all()
            database.session.close()

    @mock.patch(
        'braintree.Customer.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.CUSTOMER_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Customer.find',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.CUSTOMER_FIND_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Transaction.sale',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.SALE_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Subscription.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.SUBSCRIPTION_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.PaymentMethod.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.PAYMENT_METHOD_CREATE_SUCCESSFUL )
    )
    @mock.patch( 'application.helpers.ultsys_user.get_ultsys_user', side_effect=get_ultsys_user )
    @mock.patch( 'application.helpers.build_models.create_user', side_effect=create_user )
    @mock.patch( 'application.helpers.build_models.update_ultsys_user', side_effect=update_ultsys_user )
    @mock.patch( 'application.controllers.donate.redis_queue_caging.queue', side_effect=mock_caging )
    def test_donation_new_donor(
            self,
            ultsys_user_function,
            create_ultsys_user_function,
            update_ultsys_user_function,
            mock_caging_function
    ):  # pylint: disable=unused-argument
        """Test Braintree sale for a new donor.

        :param ultsys_user_function: Argument for mocked function.
        :param ultsys_user_update_function: Argument for mocked function.
        :param ultsys_user_create_function: Argument for mocked function.
        :return:
        """
        with self.app.app_context():
            # Create agent ( Braintree ) for the online donation.

            agent_dict = get_agent_dict()
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )

            # Flush to get the ID and set the database.
            database.session.flush()
            database.session.commit()
            agent_id = agent_model.data.id

            # Call the function to be tested.
            payload = get_donate_dict({
                'user': get_new_donor_dict(),
                'recurring_subscription': False
            })
            result = post_donation( payload )

            self.assertEqual( result[ 'job_id' ], 'redis-queue-job-id' )

            # The function should create one transaction, a gift, and a user.
            transaction = TransactionModel.query.filter_by( id=1 ).one_or_none()
            gift = GiftModel.query.filter_by( id=1 ).one_or_none()

            self.assertEqual( transaction.gift_id, gift.id )
            self.assertEqual( transaction.enacted_by_agent_id, agent_id )
            self.assertEqual( transaction.type, self.parameters[ 'transaction_type' ] )
            self.assertEqual( transaction.status, self.parameters[ 'transaction_status' ] )
            self.assertEqual( transaction.reference_number, self.parameters[ 'reference_number' ] )
            self.assertEqual( transaction.gross_gift_amount, self.parameters[ 'gross_gift_amount' ] )
            self.assertEqual( transaction.fee, self.parameters[ 'fee' ] )

            self.assertEqual( str( gift.user_id ), self.parameters[ 'user_new_id' ] )
            self.assertEqual( gift.method_used_id, self.method_used_id )
            self.assertEqual( gift.given_to, self.parameters[ 'given_to' ] )

    @mock.patch(
        'braintree.Customer.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.CUSTOMER_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Customer.find',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.CUSTOMER_FIND_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Transaction.sale',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.SALE_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Subscription.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.SUBSCRIPTION_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.PaymentMethod.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.PAYMENT_METHOD_CREATE_SUCCESSFUL )
    )
    @mock.patch( 'application.helpers.ultsys_user.get_ultsys_user', side_effect=get_ultsys_user )
    @mock.patch( 'application.helpers.build_models.update_ultsys_user', side_effect=update_ultsys_user )
    @mock.patch( 'application.controllers.donate.redis_queue_caging.queue', side_effect=mock_caging )
    def test_donation_existing_donor(
            self, ultsys_user_function, build_models_function, mock_caging_function
    ):  # pylint: disable=unused-argument
        """Test Braintree sale for existing donor.

        :param ultsys_user_function: Argument for mocked function.
        :param ultsys_user_update_function: Argument for mocked function.
        :return:
        """

        with self.app.app_context():
            # Create agent ( Braintree ) for the online donation.
            agent_dict = get_agent_dict()
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )

            # Flush to get agent ID and set database.
            database.session.flush()
            agent_id = agent_model.data.id
            database.session.commit()

            # Call the function to be tested.
            payload = get_donate_dict( { 'recurring_subscription': False } )
            result = post_donation( payload )
            self.assertEqual( result[ 'job_id' ], 'redis-queue-job-id' )

            # The function should create one transaction, a gift, and update the existing user.
            transaction = TransactionModel.query.filter_by( id=1 ).one_or_none()
            gift = GiftModel.query.filter_by( id=1 ).one_or_none()

            self.assertEqual( transaction.gift_id, gift.id )
            self.assertEqual( transaction.enacted_by_agent_id, agent_id )
            self.assertEqual( transaction.type, self.parameters[ 'transaction_type' ] )
            self.assertEqual( transaction.status, self.parameters[ 'transaction_status' ] )
            self.assertEqual( transaction.reference_number, self.parameters[ 'reference_number' ] )
            self.assertEqual( transaction.gross_gift_amount, self.parameters[ 'gross_gift_amount' ] )
            self.assertEqual( transaction.fee, self.parameters[ 'fee' ] )

            self.assertEqual( gift.user_id, self.parameters[ 'user_exists_id' ] )
            self.assertEqual( gift.method_used_id, self.method_used_id )
            self.assertEqual( gift.given_to, self.parameters[ 'given_to' ] )

    @mock.patch(
        'braintree.Customer.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.CUSTOMER_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Customer.find',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.CUSTOMER_FIND_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Transaction.sale',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.SALE_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Customer.update',
        staticmethod( lambda x, y: tests.helpers.mock_braintree_objects.MockObjects.CUSTOMER_UPDATE_SUCCESSFUL )
    )
    @mock.patch( 'application.helpers.ultsys_user.get_ultsys_user', side_effect=get_ultsys_user )
    @mock.patch( 'application.helpers.build_models.create_user', side_effect=create_user )
    @mock.patch( 'application.helpers.build_models.update_ultsys_user', side_effect=update_ultsys_user )
    @mock.patch( 'application.controllers.donate.redis_queue_caging.queue', side_effect=mock_caging )
    def test_donation_donor_update(
            self, ultsys_user_function,
            create_ultsys_user_function,
            update_ultsys_user_function,
            mock_caging_function
    ):  # pylint: disable=unused-argument
        """Test Braintree sale where there is an update to Braintree customer address.

        :param ultsys_user_function: Argument for mocked function.
        :param ultsys_user_update_function: Argument for mocked function.
        :param ultsys_user_create_function: Argument for mocked function.
        :return:
        """
        with self.app.app_context():
            # Create agent ( Braintree ) for the online donation.
            agent_dict = get_agent_dict()
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )
            database.session.commit()

            # Call function to be tested with new billing information.
            # See customer_details in TRANSACTION_SUCCESSFUL.
            new_info = {
                'user': {
                    'id': 5,
                    'user_address': {
                        'user_address': '126 Jackson Street',
                        'user_zipcode': '48336'
                    }
                }
            }

            payload = get_donate_dict( new_info )
            result = post_donation( payload )

            self.assertEqual( result[ 'job_id' ], 'redis-queue-job-id' )

            # The function should NOT update the user.
            user = UltsysUserModel.query.filter_by( ID=5 ).one_or_none()
            self.assertNotEqual( user.email, new_info[ 'user' ][ 'user_address' ][ 'user_address' ] )
            self.assertNotEqual( user.zip, int( new_info[ 'user' ][ 'user_address' ][ 'user_zipcode' ] ) )

    @mock.patch(
        'braintree.Customer.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.CUSTOMER_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Customer.find',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.CUSTOMER_FIND_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Transaction.sale',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.SALE_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Subscription.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.SUBSCRIPTION_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.PaymentMethod.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.PAYMENT_METHOD_CREATE_SUCCESSFUL )
    )
    @mock.patch( 'application.helpers.ultsys_user.get_ultsys_user', side_effect=get_ultsys_user )
    @mock.patch( 'application.controllers.donate.redis_queue_caging.queue', side_effect=mock_caging )
    def test_donation_cage_donor(
            self, ultsys_user_function, mock_caging_function
    ):   # pylint: disable=unused-argument
        """Test Braintree sale when donor is categorized as 'cage'.

        :param ultsys_user_function: Argument for mocked function.
        :return:
        """
        with self.app.app_context():
            # Create agent ( Braintree ) for the online donation.
            agent_dict = get_agent_dict()
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )

            # Flush to get agent ID and set database.
            database.session.flush()
            agent_id = agent_model.data.id
            database.session.commit()

            # Call the function to tests.
            caged_donor_dict = get_caged_donor_dict(
                { 'gift_searchable_id': uuid.uuid4(), 'customer_id': self.parameters[ 'customer_id' ] }
            )

            payload = get_donate_dict({
                'user': {
                    'user_address': {
                        'user_first_name': 'Alice',
                        'user_email_address': 'alicealbers@disney.com'
                    },
                    'billing_address': {}
                },
                'recurring_subscription': False
            })

            result = post_donation( payload )

            self.assertEqual( result[ 'job_id' ], 'redis-queue-job-id' )

            # The function should create one transaction, a gift, and a caged donor.
            # There is already one user to do the caging against.
            transaction = TransactionModel.query.filter_by( id=1 ).one_or_none()

            gift = GiftModel.query.filter_by( id=1 ).one_or_none()

            caged_donor = CagedDonorModel.query.filter_by( id=1 ).one_or_none()

            self.assertEqual( transaction.gift_id, gift.id )
            self.assertEqual( transaction.enacted_by_agent_id, agent_id )
            self.assertEqual( transaction.status, self.parameters[ 'transaction_status' ] )
            self.assertEqual( transaction.reference_number, self.parameters[ 'reference_number' ] )
            self.assertEqual( transaction.gross_gift_amount, self.parameters[ 'gross_gift_amount' ] )
            self.assertEqual( transaction.fee, self.parameters[ 'fee' ] )

            # If a donor is caged the gift.user_id will be set to 0.
            self.assertEqual( gift.user_id, -1 )
            self.assertEqual( gift.method_used_id, self.method_used_id )
            self.assertEqual( gift.given_to, self.parameters[ 'given_to' ] )

            self.assertEqual( caged_donor.gift_searchable_id, gift.searchable_id )
            self.assertEqual( caged_donor.customer_id, self.parameters[ 'customer_id' ] )
            self.assertEqual( caged_donor.user_first_name, caged_donor_dict[ 'user_first_name' ] )
            self.assertEqual( caged_donor.user_last_name, caged_donor_dict[ 'user_last_name' ] )
            self.assertEqual( caged_donor.user_address, caged_donor_dict[ 'user_address' ] )

    @mock.patch(
        'braintree.Customer.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.CUSTOMER_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Customer.find',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.CUSTOMER_FIND_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Transaction.sale',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.SALE_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.Subscription.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.SUBSCRIPTION_CREATE_SUCCESSFUL )
    )
    @mock.patch(
        'braintree.PaymentMethod.create',
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.PAYMENT_METHOD_CREATE_SUCCESSFUL )
    )
    @mock.patch( 'application.helpers.ultsys_user.get_ultsys_user', side_effect=get_ultsys_user )
    @mock.patch( 'application.controllers.donate.redis_queue_caging.queue', side_effect=mock_caging )
    def test_donation_caged_donor(
            self, ultsys_user_function, mock_caging_function
    ):  # pylint: disable=unused-argument
        """Test Braintree sale for a donor that has already been caged.

        :param ultsys_user_function: Argument for mocked function.
        :return:
        """
        with self.app.app_context():
            # Create agent ( Braintree ) for the online donation.
            agent_dict = get_agent_dict()
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )

            # Flush to get agent ID and set database.
            database.session.flush()
            agent_id = agent_model.data.id

            # Create a caged donor, which will be caged again.
            caged_donor_dict = get_caged_donor_dict(
                { 'gift_searchable_id': uuid.uuid4(), 'customer_id': self.parameters[ 'customer_id' ] }
            )

            caged_donor_model = from_json(
                CagedDonorSchema(),
                caged_donor_dict
            )
            database.session.add( caged_donor_model.data )

            database.session.commit()

            # Call function to tests.
            payload = get_donate_dict({
                'user': {
                    'user_address': {
                        'user_first_name': 'Alice',
                        'user_email_address': 'alicealbers@disney.com'
                    },
                    'billing_address': {}
                },
                'recurring_subscription': False
            })

            result = post_donation( payload )

            self.assertEqual( result[ 'job_id' ], 'redis-queue-job-id' )

            # The function should create one transaction, a gift, and an additional caged donor.
            # Additional caged donor is the same as first, but attached to a separate gift.
            transaction = TransactionModel.query.filter_by( id=1 ).one_or_none()
            gift = GiftModel.query.filter_by( id=1 ).one_or_none()
            caged_donor = CagedDonorModel.query.filter_by( id=2 ).one_or_none()

            self.assertEqual( transaction.gift_id, gift.id )
            self.assertEqual( transaction.enacted_by_agent_id, agent_id )
            self.assertEqual( transaction.type, self.parameters[ 'transaction_type' ] )
            self.assertEqual( transaction.status, self.parameters[ 'transaction_status' ] )
            self.assertEqual( transaction.reference_number, self.parameters[ 'reference_number' ] )
            self.assertEqual( transaction.gross_gift_amount, self.parameters[ 'gross_gift_amount' ] )
            self.assertEqual( transaction.fee, self.parameters[ 'fee' ])

            self.assertEqual( gift.user_id, -1 )
            self.assertEqual( gift.method_used_id, self.method_used_id )
            self.assertEqual( gift.given_to, self.parameters[ 'given_to' ] )

            self.assertEqual( caged_donor.gift_searchable_id, gift.searchable_id )
            self.assertEqual( caged_donor.customer_id, self.parameters[ 'customer_id' ] )
            self.assertEqual( caged_donor.user_first_name, caged_donor_dict[ 'user_first_name' ] )
            self.assertEqual( caged_donor.user_last_name, caged_donor_dict[ 'user_last_name' ] )
