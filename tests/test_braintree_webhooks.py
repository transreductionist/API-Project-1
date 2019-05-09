"""The module tests the subscription werbhooks by mocking the webhook notification object."""
import unittest
from decimal import Decimal

import mock
from flask_api import status

from application.app import create_app
from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from application.models.gift import GiftModel
from application.models.method_used import MethodUsedModel
from application.models.transaction import TransactionModel
from application.schemas.agent import AgentSchema
from application.schemas.gift import GiftSchema
from application.schemas.transaction import TransactionSchema
from tests.helpers.create_method_used import create_method_used
from tests.helpers.default_dictionaries import get_agent_jsons
from tests.helpers.default_dictionaries import get_gift_dict
from tests.helpers.default_dictionaries import get_transaction_dict
from tests.helpers.manage_ultsys_user_database import create_ultsys_users
from tests.helpers.mock_braintree_objects import mock_init_braintree_gateway
from tests.helpers.mock_braintree_webhooks import mock_subscription_notification
from tests.helpers.mock_ultsys_functions import get_ultsys_user


METHOD_USED = 'Web Form Credit Card'
SOURCED_FROM_AGENT = 1
RECURRING_SUBSCRIPTION_ID = 'recurring_subscription_id'


class BraintreeWebhooksTestCase( unittest.TestCase ):
    """This test suite is designed to verify the basic functionality of the Braintree webhook endpoint.

    python -m unittest discover -v
    python -m unittest -v tests.test_braintree_webhooks.BraintreeWebhooksTestCase
    python -m unittest -v tests.test_braintree_webhooks.BraintreeWebhooksTestCase.test_braintree_webhooks
    """

    def setUp( self ):
        self.app = create_app( 'TEST' )
        self.app.testing = True
        self.test_client = self.app.test_client()
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
            database.drop_all()
            database.session.commit()
            database.session.close()

    @mock.patch(
        'application.controllers.braintree_webhooks.init_braintree_gateway', side_effect=mock_init_braintree_gateway
    )
    @mock.patch(
        'application.controllers.braintree_webhooks.get_braintree_notification',
        side_effect=mock_subscription_notification
    )
    @mock.patch( 'application.helpers.general_helper_functions.get_ultsys_user', side_effect=get_ultsys_user )
    def test_braintree_webhooks(
            self,
            mock_init_gateway_function,
            mock_subscription_function,
            get_ultsys_user_function
    ):  # pylint: disable=unused-argument
        """Make sure the webhook endpoint receives a payload and makes updates as expected."""

        with self.app.app_context():
            url = '/donation/webhook/braintree/subscription'

            # Create the sourced by agent for the subscription webhook.
            agent_model = from_json( AgentSchema(), get_agent_jsons()[ 0 ], create=True )
            database.session.add( agent_model.data )
            database.session.commit()

            # Here is the first gift as check.
            gift_dict = get_gift_dict(
                {
                    'user_id': 1,
                    'method_used': METHOD_USED,
                    'sourced_from_agent_id': 1,
                    'recurring_subscription_id': 'recurring_subscription_id'
                }
            )
            gift_model = from_json( GiftSchema(), gift_dict, create=True )
            database.session.add( gift_model.data )
            database.session.flush()

            # Create a transaction on the gift.
            transaction_dict = get_transaction_dict(
                {
                    'gift_id': gift_model.data.id,
                    'enacted_by_agent_id': agent_model.data.id,
                    'type': 'Gift',
                    'gross_gift_amount': Decimal( '1.00' )
                }
            )
            transaction_model = from_json( TransactionSchema(), transaction_dict, create=True )
            database.session.add( transaction_model.data )

            database.session.commit()

            # Here is the fake POST from Braintree when the subscription webhook is triggered.
            response = self.test_client.post(
                url,
                data={ 'bt_signature': 'bt_signature', 'bt_payload': 'subscription_charged_successfully' }
            )

            self.assertEqual( response.status_code, status.HTTP_200_OK )

            method_used_id = MethodUsedModel.get_method_used( 'name', METHOD_USED ).id
            gift = GiftModel.query.filter_by( id=1 ).one_or_none()
            self.assertEqual( gift.method_used_id, method_used_id )
            self.assertEqual( gift.sourced_from_agent_id, SOURCED_FROM_AGENT )
            self.assertEqual( gift.recurring_subscription_id, RECURRING_SUBSCRIPTION_ID )

            transaction = TransactionModel.query.filter_by( id=1 ).one_or_none()
            self.assertEqual( transaction.gift_id, 1 )
            self.assertEqual( transaction.type, 'Gift' )
            self.assertEqual( transaction.status, 'Completed' )

            response = self.test_client.post(
                url,
                data={ 'bt_signature': 'bt_signature', 'bt_payload': 'subscription_charged_unsuccessfully' }
            )

            self.assertEqual( response.status_code, status.HTTP_200_OK )
            transaction = TransactionModel.query.filter_by( id=3 ).one_or_none()
            self.assertEqual( transaction.status, 'Declined' )

            response = self.test_client.post(
                url,
                data={ 'bt_signature': 'bt_signature', 'bt_payload': 'subscription_went_past_due' }
            )

            self.assertEqual( response.status_code, status.HTTP_200_OK )

            transaction = TransactionModel.query.filter_by( id=4 ).one_or_none()
            self.assertEqual( transaction.status, 'Failed' )

            response = self.test_client.post(
                url,
                data={ 'bt_signature': 'bt_signature', 'bt_payload': 'subscription_expired' }
            )

            self.assertEqual( response.status_code, status.HTTP_200_OK )

            transaction = TransactionModel.query.filter_by( id=5 ).one_or_none()
            self.assertEqual( transaction.status, 'Failed' )
