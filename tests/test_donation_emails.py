"""Tests automatic generation of several emails: receipt sent, thank you letter sent, and transaction status done."""
import unittest
from datetime import datetime

import mock

import tests.helpers.mock_braintree_objects  # pylint: disable=ungrouped-imports
from application.app import create_app
from application.controllers.donate import post_donation
from application.flask_essentials import database
from application.helpers.braintree_api import init_braintree_credentials
from application.helpers.model_serialization import from_json
from application.models.gift_thank_you_letter import GiftThankYouLetterModel
from application.models.transaction import TransactionModel
from application.schemas.agent import AgentSchema
from tests.helpers.create_method_used import create_method_used
from tests.helpers.default_dictionaries import get_agent_dict
from tests.helpers.default_dictionaries import get_donate_dict
from tests.helpers.default_dictionaries import get_new_donor_dict
from tests.helpers.mock_redis_queue_functions import mock_caging
from tests.helpers.mock_ultsys_functions import create_user
from tests.helpers.mock_ultsys_functions import get_ultsys_user
from tests.helpers.mock_ultsys_functions import update_ultsys_user


class DonationEmailsTestCase( unittest.TestCase ):
    """This test suite is designed to verify the automated email process.

    python -m unittest discover -v
    python -m unittest -v tests.test_donation_emails.DonationEmailsTestCase
    python -m unittest -v tests.test_donation_emails.DonationEmailsTestCase.test_large_donation_emails
    """

    def setUp( self ):
        self.app = create_app( 'TEST' )
        self.app.testing = True
        self.test_client = self.app.test_client()

        self.parameters = {}

        init_braintree_credentials( self.app )

        with self.app.app_context():
            database.reflect()
            database.drop_all()
            database.create_all()

            database.session.add_all( create_method_used() )
            database.session.commit()

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
    def test_small_donation_emails(
            self,
            ultsys_user_function,
            create_ultsys_user_function,
            update_ultsys_user_function,
            mock_caging_function
    ):  # pylint: disable=unused-argument
        """Test small donation does not add entry to GiftThankYouLetter table.

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

            # Call the function to be tested.
            payload = get_donate_dict( {
                'user': get_new_donor_dict(),
                'recurring_subscription': False
            } )
            post_donation( payload )

            gift_thank_you_letter = GiftThankYouLetterModel.query.filter_by( gift_id=1 ).one_or_none()
            self.assertIsNone( gift_thank_you_letter )

            transaction = TransactionModel.query.filter_by( gift_id=1 ).one_or_none()
            self.assertIsNotNone( transaction )
            self.assertIsInstance( transaction.receipt_sent_in_utc, datetime )

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
        staticmethod( lambda x: tests.helpers.mock_braintree_objects.MockObjects.SALE_CREATE_LARGE_SUCCESSFUL )
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
    def test_large_donation_emails(
            self,
            ultsys_user_function,
            create_ultsys_user_function,
            update_ultsys_user_function,
            mock_caging_function
    ):  # pylint: disable=unused-argument
        """Test large donation adds entry to GiftThankYouLetter table.

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

            # Call the function to be tested.
            payload = get_donate_dict( {
                'user': get_new_donor_dict(),
                'recurring_subscription': False,
                'transaction': { 'gross_gift_amount': '110.00' }
            } )
            post_donation( payload )

            gift_thank_you_letter = GiftThankYouLetterModel.query.filter_by( gift_id=1 ).one_or_none()
            self.assertEqual( gift_thank_you_letter.gift_id, 1 )

            transaction = TransactionModel.query.filter_by( gift_id=1 ).one_or_none()
            self.assertIsNotNone( transaction )
            self.assertIsInstance( transaction.receipt_sent_in_utc, datetime )
