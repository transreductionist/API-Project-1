"""Test module to ensure that models, Marshmallow, and session are synchronized."""
import copy
import unittest
import uuid
from datetime import datetime

import mock

from application.app import create_app
from application.flask_essentials import database
from application.helpers.build_models import build_models_sale
from application.helpers.caging import categorize_donor
from application.helpers.general_helper_functions import flatten_user_dict
from application.helpers.model_serialization import from_json
from application.models.agent import AgentModel
from application.models.caged_donor import CagedDonorModel
from application.models.campaign import CampaignAmountsModel
from application.models.campaign import CampaignModel
from application.models.gift import GiftModel
from application.models.gift_thank_you_letter import GiftThankYouLetterModel
from application.models.queued_donor import QueuedDonorModel
from application.models.transaction import TransactionModel
from application.schemas.agent import AgentSchema
from application.schemas.caged_donor import CagedDonorSchema
from application.schemas.campaign import CampaignAmountsSchema
from application.schemas.campaign import CampaignSchema
from application.schemas.gift import GiftSchema
from application.schemas.gift_thank_you_letter import GiftThankYouLetterSchema
from application.schemas.queued_donor import QueuedDonorSchema
from application.schemas.transaction import TransactionSchema
from tests.helpers.default_dictionaries import get_agent_jsons
from tests.helpers.default_dictionaries import get_caged_donor_dict
from tests.helpers.default_dictionaries import get_campaign_amount_jsons
from tests.helpers.default_dictionaries import get_campaign_dict
from tests.helpers.default_dictionaries import get_donate_dict
from tests.helpers.default_dictionaries import get_exists_donor_dict
from tests.helpers.default_dictionaries import get_gift_dict
from tests.helpers.default_dictionaries import get_new_donor_dict
from tests.helpers.default_dictionaries import get_queued_donor_dict
from tests.helpers.default_dictionaries import get_transaction_dict
from tests.helpers.manage_ultsys_user_database import create_ultsys_users
from tests.helpers.mock_ultsys_functions import create_user
from tests.helpers.mock_ultsys_functions import get_ultsys_user
from tests.helpers.mock_ultsys_functions import update_ultsys_user
from tests.helpers.model_helpers import ensure_query_session_aligned

AGENT_INDEX = 6


class DonateModelsTestCase( unittest.TestCase ):
    """This test suite is designed to verify the underlying functions that update the models and categorize a donor.

    These are core tests, and validate that, given the correct payload, the database is updated correctly. The
    functions, e.g. post_donation, admin_reallocate_gift, and admin_refund_transaction, depend upon the
    functionality tested here. Other test suites will handle the mocking of the Braintree API to ensure the
    referential integrity of the models and database.

    The first test sets rows in the database and then provides a form payload to ensure the donor is categorized
    correctly.

    Payloads are provided functions that build the application models during the Braintree transaction. These
    models include, for example, the UserModel and the GiftModel. The following tests provide appropriate payloads
    and ensure that the model is correctly updated. It makes assertions on the given model ( Model ) to ensure the
    equivalence of:
        1. model_dict[ attribute ]
        2. Model.query.filter_by( attribute=attribute )
        3. model.data.attribute ( Marshmallow instance )
        4. database.session.query( Model ).filter_by( attribute=attribute )

    python -m unittest discover -v
    python -m unittest -v tests.test_donate_models.DonateModelsTestCase
    python -m unittest -v tests.test_donate_models.DonateModelsTestCase.test_categorize_donor
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

    def tearDown( self ):
        with self.app.app_context():
            database.session.commit()
            database.session.close()

    @mock.patch( 'application.helpers.ultsys_user.get_ultsys_user', side_effect=get_ultsys_user )
    def test_categorize_donor( self, ultsys_user_function ):  # pylint: disable=unused-argument
        """The caging process categorizes donors as new, exists, cage, or caged. This function tests this process."""

        with self.app.app_context():
            # Use an existing user so category is exists.
            category = categorize_donor( flatten_user_dict( get_exists_donor_dict() ) )
            self.assertEqual( category[ 0 ], 'exists' )

            # Use a caged donor so category is caged.
            caged_donor_dict = get_caged_donor_dict( { 'gift_searchable_id': uuid.uuid4() } )
            caged_donor = from_json( CagedDonorSchema(), caged_donor_dict )
            database.session.add( caged_donor.data )
            database.session.commit()
            category = categorize_donor( caged_donor_dict )
            self.assertEqual( category[ 0 ], 'caged' )

            # Use the existing user, change the name so category is cage.
            cage_donor = copy.deepcopy( get_exists_donor_dict() )
            cage_donor[ 'user_address' ][ 'user_first_name' ] = 'Sherry'
            category = categorize_donor( flatten_user_dict( cage_donor ) )
            self.assertEqual( category[ 0 ], 'cage' )

            # Get a new donor so category is new.
            category = categorize_donor( flatten_user_dict( get_new_donor_dict() ) )
            self.assertEqual( category[ 0 ], 'new' )

    def test_agent_model( self ):
        """A test to ensure that gifts are saved correctly to the database."""

        with self.app.app_context():

            agent_dict = get_agent_jsons()[ AGENT_INDEX ]

            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )
            database.session.commit()

            agent_query = AgentModel.query\
                .filter_by( user_id=agent_dict[ 'user_id' ] ).one()
            agent_session = database.session.query( AgentModel )\
                .filter_by( user_id=agent_dict[ 'user_id' ] ).one()

            kwargs = {
                'self': self, 'model_dict': agent_dict, 'model': AgentModel, 'model_data': agent_model.data,
                'model_query': agent_query, 'model_session': agent_session
            }
            ensure_query_session_aligned( kwargs )

    def test_gift_thank_you_model( self ):
        """A test to ensure that gifts are saved correctly to the database."""

        with self.app.app_context():

            gift_thank_you_dict = { 'gift_id': 1 }

            gift_thank_you_model = from_json( GiftThankYouLetterSchema(), gift_thank_you_dict, create=True )
            database.session.add( gift_thank_you_model.data )
            database.session.commit()

            gift_thank_you_query = GiftThankYouLetterModel.query\
                .filter_by( gift_id=gift_thank_you_dict[ 'gift_id' ] ).one()
            gift_thank_you_session = database.session.query( GiftThankYouLetterModel )\
                .filter_by( gift_id=gift_thank_you_dict[ 'gift_id' ] ).one()

            kwargs = {
                'self': self, 'model_dict': gift_thank_you_dict, 'model': GiftThankYouLetterModel,
                'model_data': gift_thank_you_model.data, 'model_query': gift_thank_you_query,
                'model_session': gift_thank_you_session
            }
            ensure_query_session_aligned( kwargs )

    def test_gift_model( self ):
        """A test to ensure that gifts are saved correctly to the database."""

        with self.app.app_context():

            gift_dict = get_gift_dict(
                {
                    'user_id': 1,
                    'recurring_subscription_id': 'abcdefg'
                }
            )

            gift_model = from_json( GiftSchema(), gift_dict, create=True )
            database.session.add( gift_model.data )
            database.session.commit()

            gift_query = GiftModel.query.filter_by( user_id=gift_dict[ 'user_id' ] ).one()
            gift_session = database.session.query( GiftModel ).filter_by( user_id=gift_dict[ 'user_id' ] ).one()

            kwargs = {
                'self': self, 'model_dict': gift_dict, 'model': GiftModel, 'model_data': gift_model.data,
                'model_query': gift_query, 'model_session': gift_session
            }
            ensure_query_session_aligned( kwargs )

    def test_transaction_model( self ):
        """A test to ensure that transactions are saved correctly to the database."""

        with self.app.app_context():
            transaction_dict = get_transaction_dict( { 'gift_id': 1 } )

            transaction_model = from_json( TransactionSchema(), transaction_dict, create=True )
            database.session.add( transaction_model.data )
            database.session.commit()

            transaction_query = TransactionModel.query.filter_by( gift_id=transaction_dict[ 'gift_id' ] ).one()
            transaction_session = database.session.query( TransactionModel )\
                .filter_by( gift_id=transaction_dict[ 'gift_id' ] )\
                .one()

            kwargs = {
                'self': self, 'model_dict': transaction_dict,
                'model': TransactionModel,
                'model_data': transaction_model.data,
                'model_query': transaction_query,
                'model_session': transaction_session
            }
            ensure_query_session_aligned( kwargs )

    def test_caged_donor_model( self ):
        """A test to ensure that caged donors are saved correctly to the database."""

        with self.app.app_context():
            caged_donor_dict = get_caged_donor_dict(
                { 'gift_id': 1, 'gift_searchable_id': uuid.uuid4(), 'customer_id': 'customer_id' }
            )

            caged_donor_model = from_json( CagedDonorSchema(), caged_donor_dict, create=True )
            database.session.add( caged_donor_model.data )
            database.session.commit()

            caged_donor_query = CagedDonorModel.query\
                .filter_by( customer_id=caged_donor_dict[ 'customer_id' ] ).one()
            caged_donor_session = database.session.query( CagedDonorModel )\
                .filter_by( customer_id=caged_donor_dict[ 'customer_id' ] ).one()

            kwargs = {
                'self': self, 'model_dict': caged_donor_dict, 'model': CagedDonorModel,
                'model_data': caged_donor_model.data, 'model_query': caged_donor_query,
                'model_session': caged_donor_session
            }
            ensure_query_session_aligned( kwargs )

    def test_queued_donor_model( self ):
        """A test to ensure that caged donors are saved correctly to the database."""

        with self.app.app_context():
            queued_donor_dict = get_queued_donor_dict(
                { 'gift_id': 1, 'gift_searchable_id': uuid.uuid4(), 'customer_id': 'customer_id' }
            )

            queued_donor_model = from_json( QueuedDonorSchema(), queued_donor_dict, create=True )
            database.session.add( queued_donor_model.data )
            database.session.commit()

            queued_donor_query = QueuedDonorModel.query \
                .filter_by( customer_id=queued_donor_dict[ 'customer_id' ] ).one()
            queued_donor_session = database.session.query( QueuedDonorModel ) \
                .filter_by( customer_id=queued_donor_dict[ 'customer_id' ] ).one()

            kwargs = {
                'self': self, 'model_dict': queued_donor_dict, 'model': QueuedDonorModel,
                'model_data': queued_donor_model.data, 'model_query': queued_donor_query,
                'model_session': queued_donor_session
            }
            ensure_query_session_aligned( kwargs )

    def test_campaign_model( self ):
        """A test to ensure that campaigns are saved correctly to the database."""

        with self.app.app_context():
            campaign_dict = get_campaign_dict()

            campaign_model = from_json( CampaignSchema(), campaign_dict, create=True )
            database.session.add( campaign_model.data )
            database.session.commit()

            campaign_query = CampaignModel.query.filter_by( name=campaign_dict[ 'name' ] ).one()
            campaign_session = database.session.query( CampaignModel )\
                .filter_by( name=campaign_dict[ 'name' ] ).one()

            kwargs = {
                'self': self, 'model_dict': campaign_dict, 'model': CampaignModel,
                'model_data': campaign_model.data, 'model_query': campaign_query,
                'model_session': campaign_session
            }
            ensure_query_session_aligned( kwargs )

    def test_campaign_amounts_model( self ):
        """A test to ensure that campaign amounts are saved correctly to the database."""

        with self.app.app_context():
            # campaign_amounts_dict = get_campaign_amounts_dict()
            #
            # campaign_amounts_model = from_json( CampaignAmountsSchema(), campaign_amounts_dict, create=True )
            # database.session.add( campaign_amounts_model.data )
            # database.session.commit()

            campaign_amounts = get_campaign_amount_jsons()
            campaign_amount_dict = campaign_amounts[ 0 ]
            campaign_amount_model = from_json( CampaignAmountsSchema(), campaign_amount_dict, create=True )
            database.session.add( campaign_amount_model.data )
            database.session.commit()

            campaign_amount_query = CampaignAmountsModel.query\
                .filter_by( campaign_id=campaign_amount_dict[ 'campaign_id' ] ).one()
            campaign_amount_session = database.session.query( CampaignAmountsModel ) \
                .filter_by( campaign_id=campaign_amount_dict[ 'campaign_id' ] ).one()

            kwargs = {
                'self': self, 'model_dict': campaign_amount_dict, 'model': CampaignAmountsModel,
                'model_data': campaign_amount_model.data, 'model_query': campaign_amount_query,
                'model_session': campaign_amount_session
            }
            ensure_query_session_aligned( kwargs )

    @mock.patch( 'application.helpers.ultsys_user.get_ultsys_user', side_effect=get_ultsys_user )
    @mock.patch( 'application.helpers.build_models.update_ultsys_user', side_effect=update_ultsys_user )
    @mock.patch( 'application.helpers.build_models.create_user', side_effect=create_user )
    def test_build_models(
            self, ultsys_user_function, create_ultsys_user_function, update_ultsys_user_function
    ):  # pylint: disable=unused-argument
        """A test to ensure that the helper function build_models() correctly populates the database."""

        with self.app.app_context():
            update_dict = {
                'gift': {
                    'recurring_subscription_id': 1,
                    'sourced_from_agent_id': 'Braintree'
                }
            }
            payload_dict = get_donate_dict( update_dict )
            payload_dict[ 'user' ][ 'category' ] = 'new'
            payload_dict[ 'user' ][ 'customer_id' ] = 'customer_id'
            payload_dict[ 'transaction' ][ 'date_in_utc' ] = datetime.utcnow().strftime( '%Y-%m-%d %H:%M:%S' )
            payload_dict[ 'transaction' ][ 'fee' ] = '0.00'

            # The build_models function expects a list of transactions.
            payload_dict[ 'transactions' ] = [ payload_dict[ 'transaction' ] ]

            build_models_sale( payload_dict[ 'user' ], payload_dict[ 'gift' ], payload_dict[ 'transactions' ] )
