"""Module that tests a donation made by administrative staff."""
import unittest
import uuid
from decimal import Decimal

import mock

from application.app import create_app
from application.controllers.donate import post_donation
from application.flask_essentials import database
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
from tests.helpers.default_dictionaries import get_exists_donor_dict
from tests.helpers.default_dictionaries import get_new_donor_dict
from tests.helpers.manage_ultsys_user_database import create_ultsys_users
from tests.helpers.mock_redis_queue_functions import mock_caging
from tests.helpers.mock_ultsys_functions import create_user
from tests.helpers.mock_ultsys_functions import get_ultsys_user
from tests.helpers.mock_ultsys_functions import update_ultsys_user
from tests.helpers.ultsys_user_model import UltsysUserModel


class AdminDonateTestCase( unittest.TestCase ):
    """This test suite is designed to verify the administrative donation process for items like checks.

    One important aspect of the tests is that they are designed to validate the referential integrity of the models
    and database when a donation is created. A donation will create a transaction, gift, and a donor in the
    database, which refer to one another. The donor may be a new, or existing donor. They may also be a new, or
    existing caged donor.

    This is a different path from online donations, specifically it does not use the Braintree API, and relies on
    other code to manage taking the payload and building the models. It is used for recording checks, and other
    similar types of donations.

    python -m unittest discover -v
    python -m unittest -v tests.test_admin_donate.AdminDonateTestCase
    python -m unittest -v tests.test_admin_donate.AdminDonateTestCase.test_admin_new_donor
    """

    def setUp( self ):
        self.app = create_app( 'TEST' )
        self.app.testing = True
        self.test_client = self.app.test_client()
        self.parameters = {
            'reference_number': '101',
            'method_used': 'Check',
            'date_of_method_used': '2018-07-12 00:00:00',
            'given_to': 'NERF',
            'transaction_type': 'Gift',
            'gross_gift_amount': Decimal( 10.00 ),
            'transaction_status': 'Completed',
            'new_user_email': 'larryalbers@gmail.com',
            'customer_id': 'customer_id',
            'second_transaction_type': 'Deposit to Bank',
            'bank_deposit_number': '<bank-deposit-number>'
        }

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
            database.session.commit()
            database.session.close()

    @mock.patch( 'application.helpers.ultsys_user.get_ultsys_user', side_effect=get_ultsys_user )
    @mock.patch( 'application.helpers.build_models.update_ultsys_user', side_effect=update_ultsys_user )
    @mock.patch( 'application.helpers.build_models.create_user', side_effect=create_user )
    @mock.patch( 'application.controllers.donate.redis_queue_caging.queue', side_effect=mock_caging )
    def test_admin_new_donor(
            self,
            ultsys_user_function,
            create_ultsys_user_function,
            update_ultsys_user_function,
            mock_caging_function
    ):  # pylint: disable=unused-argument
        """Test the administrative donation of a donor who is a new user."""

        with self.app.app_context():

            # Create the sourced by agent.
            agent_dict = get_agent_dict( { 'name': 'Unspecified NumbersUSA Staff' } )
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )
            database.session.flush()
            database.session.commit()

            agent_dict = get_agent_dict( { 'name': 'Fidelity Bank' } )
            bank_agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( bank_agent_model.data )
            database.session.flush()
            database.session.commit()

            # Create the agent who will be referenced in the payload.
            agent_user_id = '3255162'
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
            database.session.commit()

            # Call the function to be tested.
            # Administrative donations need to provide information not required by an online donation.
            payload = get_donate_dict( {
                'gift': {
                    'method_used': self.parameters[ 'method_used' ],
                },
                'transaction': {
                    'date_of_method_used': self.parameters[ 'date_of_method_used' ]
                },
                'user': get_new_donor_dict(),
                'recurring_subscription': False
            } )
            payload[ 'sourced_from_agent_user_id' ] = agent_user_id

            payload[ 'transaction' ][ 'reference_number' ] = self.parameters[ 'reference_number' ]
            payload[ 'transaction' ][ 'type' ] = self.parameters[ 'transaction_type' ]

            self.assertEqual( post_donation( payload )[ 'job_id' ], 'redis-queue-job-id' )

            # The function should create one transaction, a gift, and a user.
            transactions = TransactionModel.query.all()
            gift = GiftModel.query.filter_by( id=1 ).one_or_none()

            self.assertEqual( transactions[ 0 ].gift_id, gift.id )
            self.assertEqual( transactions[ 0 ].enacted_by_agent_id, 3 )
            self.assertEqual( transactions[ 0 ].type, self.parameters[ 'transaction_type' ] )
            self.assertEqual( transactions[ 0 ].status, self.parameters[ 'transaction_status' ] )
            self.assertEqual( transactions[ 0 ].reference_number, self.parameters[ 'reference_number' ] )
            self.assertEqual( transactions[ 0 ].gross_gift_amount, self.parameters[ 'gross_gift_amount' ] )

            self.assertEqual( transactions[ 1 ].gift_id, gift.id )
            self.assertEqual( transactions[ 1 ].enacted_by_agent_id, 2 )
            self.assertEqual( transactions[ 1 ].type, self.parameters[ 'second_transaction_type' ] )
            self.assertEqual( transactions[ 1 ].status, self.parameters[ 'transaction_status' ] )
            self.assertEqual( transactions[ 1 ].reference_number, self.parameters[ 'bank_deposit_number' ] )
            self.assertEqual( transactions[ 1 ].gross_gift_amount, self.parameters[ 'gross_gift_amount' ] )

            # Find the newly created Ultsys ID.
            ultsys_user = UltsysUserModel.query.filter_by( email=self.parameters[ 'new_user_email' ] ).one_or_none()

            self.assertEqual( gift.user_id, ultsys_user.ID )
            self.assertEqual( gift.method_used_id, self.method_used_id )
            self.assertEqual( gift.given_to, self.parameters[ 'given_to' ] )

    @mock.patch( 'application.helpers.ultsys_user.get_ultsys_user', side_effect=get_ultsys_user )
    @mock.patch( 'application.helpers.build_models.update_ultsys_user', side_effect=update_ultsys_user )
    @mock.patch( 'application.controllers.donate.redis_queue_caging.queue', side_effect=mock_caging )
    def test_admin_existing_donor(
            self,
            ultsys_user_function,
            update_ultsys_user_function,
            mock_caging_function
    ):  # pylint: disable=unused-argument
        """Test the administrative donation of a donor who is an existing user."""

        with self.app.app_context():
            # Create the sourced by agent.
            agent_dict = get_agent_dict( { 'name': 'Unspecified NumbersUSA Staff' } )
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )
            database.session.flush()
            database.session.commit()

            agent_dict = get_agent_dict( { 'name': 'Fidelity Bank' } )
            bank_agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( bank_agent_model.data )
            database.session.flush()
            database.session.commit()

            # Create the agent who will be referenced in the payload.
            agent_user_id = '3255162'
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
            database.session.commit()

            # Call the function to be tested.
            # Administrative donations need to provide information not required by an online donation.
            payload = get_donate_dict({
                'gift': {
                    'method_used': self.parameters[ 'method_used' ],
                },
                'transaction': {
                    'date_of_method_used': self.parameters[ 'date_of_method_used' ]
                },
                'user': get_exists_donor_dict(),
                'recurring_subscription': False
            })
            payload[ 'sourced_from_agent_user_id' ] = agent_user_id
            payload[ 'transaction' ][ 'reference_number' ] = self.parameters[ 'reference_number' ]
            payload[ 'transaction' ][ 'type' ] = self.parameters[ 'transaction_type' ]

            self.assertEqual( post_donation( payload )[ 'job_id' ], 'redis-queue-job-id' )

            # The function should create one transaction, a gift, and a user.
            transactions = TransactionModel.query.all()
            gift = GiftModel.query.filter_by( id=1 ).one_or_none()

            self.assertEqual( transactions[ 0 ].gift_id, gift.id )
            self.assertEqual( transactions[ 0 ].enacted_by_agent_id, 3 )
            self.assertEqual( transactions[ 0 ].type, self.parameters[ 'transaction_type' ] )
            self.assertEqual( transactions[ 0 ].status, self.parameters[ 'transaction_status' ] )
            self.assertEqual( transactions[ 0 ].reference_number, self.parameters[ 'reference_number' ] )
            self.assertEqual( transactions[ 0 ].gross_gift_amount, self.parameters[ 'gross_gift_amount' ] )

            self.assertEqual( transactions[ 1 ].gift_id, gift.id )
            self.assertEqual( transactions[ 1 ].enacted_by_agent_id, 2 )
            self.assertEqual( transactions[ 1 ].type, self.parameters[ 'second_transaction_type' ] )
            self.assertEqual( transactions[ 1 ].status, self.parameters[ 'transaction_status' ] )
            self.assertEqual( transactions[ 1 ].reference_number, self.parameters[ 'bank_deposit_number' ] )
            self.assertEqual( transactions[ 1 ].gross_gift_amount, self.parameters[ 'gross_gift_amount' ] )

            self.assertEqual( gift.user_id, 5 )
            self.assertEqual( gift.method_used_id, self.method_used_id )
            self.assertEqual( gift.given_to, self.parameters[ 'given_to' ] )

    @mock.patch( 'application.helpers.ultsys_user.get_ultsys_user', side_effect=get_ultsys_user )
    @mock.patch( 'application.controllers.donate.redis_queue_caging.queue', side_effect=mock_caging )
    def test_admin_cage_donor(
            self,
            ultsys_user_function,
            mock_caging_function
    ):  # pylint: disable=unused-argument
        """Test the administrative donation of a donor who has to be caged."""

        with self.app.app_context():
            # Create the sourced by agent.
            agent_dict = get_agent_dict( { 'name': 'Unspecified NumbersUSA Staff' } )
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )
            database.session.flush()
            database.session.commit()

            agent_dict = get_agent_dict( { 'name': 'Fidelity Bank' } )
            bank_agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( bank_agent_model.data )
            database.session.flush()
            database.session.commit()

            # Create the agent who will be referenced in the payload.
            agent_user_id = '3255162'
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
            database.session.commit()

            # Call the function to be tested.
            # Administrative donations need to provide information not required by an online donation.
            payload = get_donate_dict({
                'gift': {
                    'method_used': self.parameters[ 'method_used' ],
                },
                'transaction': {
                    'date_of_method_used': self.parameters[ 'date_of_method_used' ]
                },
                'user': {
                    'user_address': {
                        'user_first_name': 'Alice',
                        'user_email_address': 'alicealbers@disney.com'
                    },
                    'billing_address': {}
                },
                'recurring_subscription': False
            })
            payload[ 'sourced_from_agent_user_id' ] = agent_user_id
            payload[ 'transaction' ][ 'reference_number' ] = self.parameters[ 'reference_number' ]
            payload[ 'transaction' ][ 'type' ] = self.parameters[ 'transaction_type' ]

            self.assertEqual( post_donation( payload )[ 'job_id' ], 'redis-queue-job-id' )

            # The function should create one transaction, a gift, and a user.
            transactions = TransactionModel.query.all()
            gift = GiftModel.query.filter_by( id=1 ).one_or_none()

            self.assertEqual( transactions[ 0 ].gift_id, gift.id )
            self.assertEqual( transactions[ 0 ].enacted_by_agent_id, 3 )
            self.assertEqual( transactions[ 0 ].type, self.parameters[ 'transaction_type' ] )
            self.assertEqual( transactions[ 0 ].status, self.parameters[ 'transaction_status' ] )
            self.assertEqual( transactions[ 0 ].reference_number, self.parameters[ 'reference_number' ] )
            self.assertEqual( transactions[ 0 ].gross_gift_amount, self.parameters[ 'gross_gift_amount' ] )

            self.assertEqual( transactions[ 1 ].gift_id, gift.id )
            self.assertEqual( transactions[ 1 ].enacted_by_agent_id, 2 )
            self.assertEqual( transactions[ 1 ].type, self.parameters[ 'second_transaction_type' ] )
            self.assertEqual( transactions[ 1 ].status, self.parameters[ 'transaction_status' ] )
            self.assertEqual( transactions[ 1 ].reference_number, self.parameters[ 'bank_deposit_number' ] )
            self.assertEqual( transactions[ 1 ].gross_gift_amount, self.parameters[ 'gross_gift_amount' ] )

            caged_donor_dict = get_caged_donor_dict()
            caged_donor = CagedDonorModel.query.first()
            self.assertEqual( caged_donor.gift_searchable_id, gift.searchable_id )
            self.assertEqual( caged_donor.user_first_name, caged_donor_dict[ 'user_first_name' ] )
            self.assertEqual( caged_donor.user_last_name, caged_donor_dict[ 'user_last_name' ] )

    @mock.patch( 'application.helpers.ultsys_user.get_ultsys_user', side_effect=get_ultsys_user )
    @mock.patch( 'application.controllers.donate.redis_queue_caging.queue', side_effect=mock_caging )
    def test_admin_caged_donor(
            self,
            ultsys_user_function,
            mock_caging_function
    ):  # pylint: disable=unused-argument
        """Test the administrative donation of a donor who has been previously caged."""

        with self.app.app_context():
            agent_dict = get_agent_dict( { 'name': 'Unspecified NumbersUSA Staff' } )
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )
            database.session.flush()
            database.session.commit()

            agent_dict = get_agent_dict( { 'name': 'Fidelity Bank' } )
            bank_agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( bank_agent_model.data )
            database.session.flush()
            database.session.commit()

            # Create the agent who will be referenced in the payload.
            agent_user_id = '3255162'
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
            database.session.commit()

            # Create a caged donor, which will be caged again.
            caged_donor_dict = get_caged_donor_dict(
                { 'gift_searchable_id': uuid.uuid4(), 'customer_id': self.parameters[ 'customer_id' ] }
            )
            caged_donor_model = from_json(
                CagedDonorSchema(),
                caged_donor_dict,
                create=True
            )
            database.session.add( caged_donor_model.data )
            database.session.flush()
            database.session.commit()

            # Call function to tests.
            payload = get_donate_dict(
                {
                    'gift': {
                        'method_used': self.parameters[ 'method_used' ],
                        'date_of_method_used': self.parameters[ 'date_of_method_used' ]
                    },
                    'user': {
                        'user_address': {
                            'user_first_name': caged_donor_model.data.user_first_name,
                            'user_last_name': caged_donor_model.data.user_last_name,
                            'user_address': caged_donor_model.data.user_address
                        }
                    }
                }
            )
            payload[ 'sourced_from_agent_user_id' ] = agent_user_id
            payload[ 'transaction' ][ 'reference_number' ] = self.parameters[ 'reference_number' ]
            payload[ 'transaction' ][ 'type' ] = self.parameters[ 'transaction_type' ]

            self.assertEqual( post_donation( payload )[ 'job_id' ], 'redis-queue-job-id' )

            # The function should create one transaction, a gift, and a user.
            transactions = TransactionModel.query.all()
            gift = GiftModel.query.filter_by( id=1 ).one_or_none()

            self.assertEqual( transactions[ 0 ].gift_id, gift.id )
            self.assertEqual( transactions[ 0 ].enacted_by_agent_id, 3 )
            self.assertEqual( transactions[ 0 ].type, self.parameters[ 'transaction_type' ] )
            self.assertEqual( transactions[ 0 ].status, self.parameters[ 'transaction_status' ] )
            self.assertEqual( transactions[ 0 ].reference_number, self.parameters[ 'reference_number' ] )
            self.assertEqual( transactions[ 0 ].gross_gift_amount, self.parameters[ 'gross_gift_amount' ] )

            self.assertEqual( transactions[ 1 ].gift_id, gift.id )
            self.assertEqual( transactions[ 1 ].enacted_by_agent_id, 2 )
            self.assertEqual( transactions[ 1 ].type, self.parameters[ 'second_transaction_type' ] )
            self.assertEqual( transactions[ 1 ].status, self.parameters[ 'transaction_status' ] )
            self.assertEqual( transactions[ 1 ].reference_number, self.parameters[ 'bank_deposit_number' ] )
            self.assertEqual( transactions[ 1 ].gross_gift_amount, self.parameters[ 'gross_gift_amount' ] )

            caged_donor = CagedDonorModel.query.filter_by( id=2 ).one()

            self.assertEqual( caged_donor.gift_searchable_id, gift.searchable_id )
            self.assertEqual( caged_donor.user_first_name, caged_donor_dict[ 'user_first_name' ] )
            self.assertEqual( caged_donor.user_last_name, caged_donor_dict[ 'user_last_name' ] )
