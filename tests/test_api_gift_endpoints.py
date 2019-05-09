"""The module tests each Gift API endpoint to ensure a request is successfully made and valid data returned."""
import json
import unittest
import uuid
from datetime import datetime
from datetime import timedelta

from flask_api import status

from application.app import create_app
from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from application.models.gift import GiftModel
from application.models.transaction import TransactionModel
from application.schemas.agent import AgentSchema
from application.schemas.gift import GiftSchema
from application.schemas.transaction import TransactionSchema
from tests.helpers.default_dictionaries import get_agent_dict
from tests.helpers.default_dictionaries import get_gift_dict
from tests.helpers.default_dictionaries import get_gift_searchable_ids
from tests.helpers.default_dictionaries import get_transaction_dict
from tests.helpers.mock_jwt_functions import ACCESS_TOKEN
from tests.helpers.model_helpers import create_gift_transactions_date
from tests.helpers.model_helpers import create_model_list


class APIGiftEndpointsTestCase( unittest.TestCase ):
    """This test suite is designed to verify the basic functionality of the API Gift endpoints.

    All endpoints that retrieve data from the database are tested here. These include any calls which are performing
    queries before returning data.

    The endpoints that depend upon the Braintree API need to be mocked and are tested elsewhere.

    python -m unittest discover -v
    python -m unittest -v tests.test_api_gift_endpoints.APIGiftEndpointsTestCase
    python -m unittest -v tests.test_api_gift_endpoints.APIGiftEndpointsTestCase.test_get_gifts_with_id
    """

    def setUp( self ):
        self.app = create_app( 'TEST' )
        self.app.testing = True
        self.test_client = self.app.test_client()
        self.test_client = self.app.test_client()
        self.access_token = ACCESS_TOKEN
        self.headers = { 'Authorization': 'Bearer {}'.format( self.access_token ) }
        with self.app.app_context():
            database.reflect()
            database.drop_all()
            database.create_all()

    def tearDown( self ):
        with self.app.app_context():
            database.session.commit()
            database.session.close()

    def test_get_gifts( self ):
        """Gifts endpoint with no ID's retrieves all ( methods = [ GET ] )."""

        with self.app.app_context():
            url = '/donation/gifts'

            # Ensure a GET with no saved gifts returns 0.
            response = self.test_client.get( url, headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 0 )

            # To create each gift with a new UUID call get_gift_dict() separately.
            total_gifts = 5
            gift_models = []
            for i in range( 0, total_gifts ):  # pylint: disable=W0612
                gift_json = get_gift_dict()
                del gift_json[ 'id' ]
                gift_json[ 'searchable_id' ] = uuid.uuid4()
                gift_model = GiftSchema().load( gift_json ).data
                gift_models.append( gift_model )
            database.session.bulk_save_objects( gift_models )
            database.session.commit()

            # Ensure GET returns all gifts.
            response = self.test_client.get( url, headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), total_gifts )

            # Ensure GET retrieves 2 gifts and they have the correct ID's.
            searchable_ids = [ str( gift_models[ 0 ].searchable_id ), str( gift_models[ 1 ].searchable_id ) ]
            searchable_id_parameters = 'in:{},{}'.format( searchable_ids[ 0 ], searchable_ids[ 1 ] )
            url_with_parameters = '{}?searchable_id={}'.format( url, searchable_id_parameters )
            response = self.test_client.get( url_with_parameters, headers=self.headers )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 2 )
            self.assertEqual( data_returned[ 0 ][ 'searchable_id' ], searchable_ids[ 0 ] )
            self.assertEqual( data_returned[ 1 ][ 'searchable_id' ], searchable_ids[ 1 ] )

    def test_get_gifts_with_id( self ):
        """Gifts-transaction endpoint with one gift ID retrieves all transactions on gift ( methods = [ GET ] )."""

        with self.app.app_context():
            url = '/donation/gifts/{}/transactions'

            # Ensure that with no database entries endpoint returns nothing.
            response = self.test_client.get( url.format( str( uuid.uuid4() ) ), headers=self.headers )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

            # Create some gifts to retrieve.
            total_gifts = 5
            gift_models = create_model_list( GiftSchema(), get_gift_dict(), total_gifts )

            # Create a set of transactions and attach to a specific gift.
            total_transactions = 5
            transaction_gift_id = 3

            transaction_models = create_model_list(
                TransactionSchema(),
                get_transaction_dict( { 'gift_id': transaction_gift_id } ),
                total_transactions
            )

            database.session.bulk_save_objects( gift_models )
            database.session.bulk_save_objects( transaction_models )
            database.session.commit()

            # Build the URL using the searchable_id of the gift.
            gift_3 = GiftModel.query.filter_by( id=3 ).one_or_none()
            searchable_id = gift_3.searchable_id

            # Ensure GET retrieves the specified gift and all its transactions.
            response = self.test_client.get( url.format( str( searchable_id ) ), headers=self.headers )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), total_transactions )

    def test_get_gifts_without_id( self ):
        """Gifts-transaction endpoint with gift ID's retrieves all transactions on gifts ( methods = [ GET ] )."""

        with self.app.app_context():
            url = '/donation/gifts/transactions'

            # Create some gifts to retrieve.
            total_gifts = 5
            gift_models = create_model_list( GiftSchema(), get_gift_dict(), total_gifts )

            # Create 2 sets of transactions, each attached to a separate gift.
            total_transactions = 5
            transaction_gift_ids = [ 2, 4 ]

            transaction_models_1 = create_model_list(
                TransactionSchema(),
                get_transaction_dict( { 'gift_id': transaction_gift_ids[ 0 ] } ),
                total_transactions
            )

            transaction_models_2 = create_model_list(
                TransactionSchema(),
                get_transaction_dict( { 'gift_id': transaction_gift_ids[ 1 ] } ),
                total_transactions
            )

            database.session.bulk_save_objects( gift_models )
            database.session.bulk_save_objects( transaction_models_1 )
            database.session.bulk_save_objects( transaction_models_2 )
            database.session.commit()

            gift_2 = GiftModel.query.filter_by( id=2 ).one_or_none()
            searchable_id_2 = gift_2.searchable_id
            gift_4 = GiftModel.query.filter_by( id=4 ).one_or_none()
            searchable_id_4 = gift_4.searchable_id

            # Ensure a GET returns all transactions.
            response = self.test_client.get( url, headers=self.headers )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 2 * total_transactions )

            # Ensure GET retrieves all transactions attached to the specified gift and the ID is correct.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'searchable_ids': [ str( searchable_id_2 ) ] } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )

            self.assertEqual( len( data_returned ), 5 )
            self.assertEqual( data_returned[ 0 ][ 'gift_searchable_id' ], str( searchable_id_2 ) )

            # Ensure GET retrieves all transactions attached to the 2 gifts.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'searchable_ids': [ str( searchable_id_2 ), str( searchable_id_4 ) ] } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 10 )

    def test_get_gifts_by_date_future( self ):
        """Gifts endpoint which retrieves all gifts newer than date, or between 2 dates ( methods = [ POST ] )."""

        with self.app.app_context():
            url = '/donation/gifts/date'

            # Ensure that with no database entries endpoint returns nothing.
            date_in_utc_now = datetime.utcnow()
            response = self.test_client.post(
                url,
                data=json.dumps( { 'date': date_in_utc_now.strftime( '%Y-%m-%d' ) } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

            # Create some gifts to retrieve.
            total_gifts = 2
            gift_models = create_model_list( GiftSchema(), get_gift_dict(), total_gifts )

            # Create a set of transactions and attach to a specific gift.
            # Here are the time deltas: { gift 1: [ 0, -2, -4, -6 ], gift 2: [ -8, -10, -12, -14 ] }
            total_transactions = 4
            transaction_models = create_gift_transactions_date(
                TransactionSchema(),
                get_transaction_dict(),
                total_transactions,
                total_gifts
            )

            database.session.bulk_save_objects( gift_models )
            database.session.bulk_save_objects( transaction_models )
            database.session.commit()

            date_in_utc_now = datetime.utcnow()

            # Date in the future should bring back no results.
            date_in_utc = date_in_utc_now + timedelta( days=2 )
            response = self.test_client.post(
                url,
                data=json.dumps( { 'date': date_in_utc.strftime( '%Y-%m-%d' ) } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

    def test_get_gifts_by_date_past( self ):
        """Gifts endpoint which retrieves all gifts newer than date, or between 2 dates ( methods = [ POST ] )."""

        with self.app.app_context():
            url = '/donation/gifts/date'

            # To create each gift with a new UUID call get_gift_dict() separately.
            totals = { 'gifts': 2, 'transactions': 4 }
            gift_models = []
            for i in range( 0, totals[ 'gifts' ] ):  # pylint: disable=W0612
                gift_json = get_gift_dict()
                del gift_json[ 'id' ]
                gift_json[ 'searchable_id' ] = uuid.uuid4()
                gift_model = GiftSchema().load( gift_json ).data
                gift_models.append( gift_model )
            database.session.bulk_save_objects( gift_models )
            database.session.commit()

            # Create a set of transactions and attach to a specific gift.
            # Here are the time deltas: { gift 1: [ 0, -2, -4, -6 ], gift 2: [ -8, -10, -12, -14 ] }
            transaction_models = create_gift_transactions_date(
                TransactionSchema(),
                get_transaction_dict(),
                totals[ 'transactions' ],
                totals[ 'gifts' ]
            )

            database.session.bulk_save_objects( transaction_models )
            database.session.commit()

            date_in_utc_now = datetime.utcnow().replace( hour=0, minute=0, second=0, microsecond=0 )

            # Date in the past on only gift 1.
            date_in_utc = date_in_utc_now - timedelta( days=2 )
            response = self.test_client.post(
                url,
                data=json.dumps( { 'date': date_in_utc.strftime( '%Y-%m-%d' ) } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )

            self.assertEqual( len( data_returned ), 1 )
            self.assertEqual( data_returned[ 0 ][ 'searchable_id' ], str( gift_models[ 0 ].searchable_id ) )

            # Date in the past which includes transactions on both gift 1 and gift 2.
            date_in_utc = date_in_utc_now - timedelta( days=10 )
            response = self.test_client.post(
                url,
                data=json.dumps( { 'date': date_in_utc.strftime( '%Y-%m-%d' ) } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )

            self.assertEqual( len( data_returned ), 2 )
            self.assertEqual( data_returned[ 0 ][ 'searchable_id' ], str( gift_models[ 0 ].searchable_id ) )
            self.assertEqual( data_returned[ 1 ][ 'searchable_id' ], str( gift_models[ 1 ].searchable_id ) )

            # Date range in the past, which includes transactions on both gift 1 and 2.
            date_in_utc_0 = date_in_utc_now - timedelta( days=6 )
            date_in_utc_1 = date_in_utc_now - timedelta( days=8 )
            response = self.test_client.post(
                url,
                data=json.dumps(
                    {
                        'date': [ date_in_utc_0.strftime( '%Y-%m-%d' ), date_in_utc_1.strftime( '%Y-%m-%d' ) ]
                    }
                ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )

            self.assertEqual( len( data_returned ), 2 )
            self.assertEqual( data_returned[ 0 ][ 'searchable_id' ], str( gift_models[ 0 ].searchable_id ) )
            self.assertEqual( data_returned[ 1 ][ 'searchable_id' ], str( gift_models[ 1 ].searchable_id ) )

            # Date in the distant past, should bring back no results.
            date_in_utc = date_in_utc_now - timedelta( days=16 )
            response = self.test_client.post(
                url,
                data=json.dumps( { 'date': date_in_utc.strftime( '%Y-%m-%d' ) } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 2 )

            # Date in the future, should bring back no results.
            date_in_utc = date_in_utc_now + timedelta( days=16 )
            response = self.test_client.post(
                url,
                data=json.dumps( { 'date': date_in_utc.strftime( '%Y-%m-%d' ) } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

    def test_get_gifts_by_given_to( self ):
        """Gifts endpoint which retrieves all gifts by given_to list ( methods = [ POST ] )."""

        with self.app.app_context():
            url = '/donation/gifts/given-to'

            # The given_to field enums: [ 'ACTION', 'NERF', 'SUPPORT' ]
            given_tos = GiftModel.given_to.property.columns[ 0 ].type.enums

            # Ensure that with no database entries endpoint returns nothing.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'given_to': given_tos[ 0 ] } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

            # Create one gift for each given_to.
            gift_models = []
            for given_to in given_tos:
                gift_model = from_json(
                    GiftSchema(),
                    get_gift_dict( { 'searchable_id': uuid.uuid4(), 'given_to': given_to } ),
                    create=True
                )
                gift_models.append( gift_model.data )

            # Create one gift with the same enumeration for return of multiple gifts.
            gift_model = from_json(
                GiftSchema(),
                get_gift_dict( { 'searchable_id': uuid.uuid4(), 'given_to': given_tos[ 0 ] } ),
                create=True
            )
            gift_models.append( gift_model.data )

            database.session.bulk_save_objects( gift_models )
            database.session.commit()

            # Ensure that with the one duplicated given_to two gifts are returned.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'given_to': given_tos[ 0 ] } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 2 )

            # Ensure that with 2 given_tos 3 gifts are returned.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'given_to': [ given_tos[ 0 ], given_tos[ 1 ] ] } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 3 )

    def test_get_gifts_by_user_id_get( self ):
        """Gifts endpoint which retrieves all gifts with given user_id ( methods = [ GET ] )."""

        with self.app.app_context():
            url = '/donation/gift/user/{}'

            # Ensure that with no database entries endpoint returns nothing.
            response = self.test_client.get( url.format( 1 ), headers=self.headers  )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

            # Create a gift with a user_id.
            gift_model = from_json(
                GiftSchema(),
                get_gift_dict( { 'searchable_id': uuid.uuid4(), 'user_id': 1 } ),
                create=True
            )
            database.session.add( gift_model.data )
            database.session.commit()

            # Ensure that with a user_id on a gift it is returned
            response = self.test_client.get( url.format( 1 ), headers=self.headers )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 1 )

    def test_get_gifts_by_user_id_post( self ):
        """Gifts endpoint which retrieves all gifts with list of given user_id's ( methods = [ POST ] )."""

        with self.app.app_context():
            url = '/donation/gift/user'

            # Ensure that with no database entries endpoint returns nothing.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'user_ids': [ 1, 3 ] } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

            # Create a gift with a user_id.
            max_number_of_users = 5
            gift_models = create_model_list(
                GiftSchema(),
                get_gift_dict(),
                max_number_of_users,
                'user_id'
            )

            database.session.bulk_save_objects( gift_models )
            database.session.commit()

            # Ensure that with no users endpoint returns no gifts.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'user_ids': [] } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

            # Ensure that with one user endpoint returns one gift.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'user_ids': [ 2 ] } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 1 )

            # Ensure that with multiple users endpoint returns multiple gifts.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'user_ids': [ 2, 3, 4 ] } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 3 )

    def test_get_gifts_partial_id( self ):
        """Gifts endpoint to get a list of Gifts given a partial searchable_id ( methods = [ GET ] )."""

        with self.app.app_context():
            # Parameter in URL is for a searchable_id_prefix.
            url = '/donation/gifts/uuid_prefix/{}'

            # Create each gift with a reproducible UUID.
            total_gifts = 5
            searchable_ids = get_gift_searchable_ids()
            gift_models = []
            for i in range( 0, total_gifts ):  # pylint: disable=W0612
                gift_json = get_gift_dict()
                del gift_json[ 'id' ]
                gift_json[ 'searchable_id' ] = searchable_ids[ i ]
                gift_model = GiftSchema().load( gift_json ).data
                gift_models.append( gift_model )
            database.session.bulk_save_objects( gift_models )
            database.session.commit()

            # searchable_ids[ 0:2 ] have the same first 5 characters: this test should return those 2.
            response = self.test_client.get( url.format( searchable_ids[ 0 ][ :5 ] ), headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 2 )

            # searchable_ids[ 1 ] shares first 5 characters, but is unique as a whole and should return 1.
            searchable_id_uuid = uuid.UUID( searchable_ids[ 1 ] ).hex
            response = self.test_client.get( url.format( searchable_id_uuid ), headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 1 )

            # searchable_ids[ 2 ] is unique and first 5 characters should return 1.
            response = self.test_client.get( url.format( searchable_ids[ 2 ][ :5 ] ), headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 1 )

            # searchable_ids[ 5 ] is not in the database.
            searchable_id_uuid = uuid.UUID( searchable_ids[ 5 ] ).hex
            response = self.test_client.get( url.format( searchable_id_uuid ), headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 0 )

    def test_put_gift_update_note( self ):
        """Gifts endpoint to add a note to a gift with searchable_id ( methods = [ PUT ] )."""

        with self.app.app_context():
            # Parameter in URL is for a searchable_id_prefix.
            url = '/donation/gift/{}/notes'

            agent_dict = get_agent_dict( { 'name': 'Aaron Peters', 'user_id': 3255162, 'type': 'Staff Member' } )
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )

            gift_transactions = TransactionModel.query.all()
            # Ensure no transactions in the database.
            self.assertEqual( len( gift_transactions ), 0 )

            gift_json = get_gift_dict()
            del gift_json[ 'id' ]
            gift_json[ 'searchable_id' ] = uuid.uuid4()
            gift_model = GiftSchema().load( gift_json ).data
            database.session.add( gift_model )
            database.session.commit()

            transaction_note = {
                'enacted_by_agent_id': '5',
                'note': 'Add this to the Gift please.'
            }

            response = self.test_client.put(
                url.format( gift_model.searchable_id.hex ),
                data=json.dumps( transaction_note ),
                content_type='application/json',
                headers=self.headers
            )

            self.assertEqual( response.status_code, status.HTTP_200_OK )

            # Make sure a transaction was added.
            gift_transactions = TransactionModel.query.all()

            self.assertEqual( len( gift_transactions ), 1 )
            self.assertEqual( gift_transactions[ 0 ].notes, transaction_note[ 'note' ] )

    def test_get_gift_update_note( self ):
        """Gifts endpoint to get a list of notes given a gift_searchable_id ( methods = [ GET ] )."""

        with self.app.app_context():
            # Parameter in URL is for a searchable_id_prefix.
            url = '/donation/gift/{}/notes'

            # Create 3 gifts to attach transactions to.
            # Create each gift with a reproducible UUID.
            total_gifts = 4
            searchable_ids = get_gift_searchable_ids()
            gift_models = [ ]
            for i in range( 0, total_gifts ):  # pylint: disable=W0612
                gift_json = get_gift_dict()
                del gift_json[ 'id' ]
                gift_json[ 'searchable_id' ] = searchable_ids[ i ]
                gift_model = GiftSchema().load( gift_json ).data
                gift_models.append( gift_model )
            database.session.bulk_save_objects( gift_models )
            database.session.commit()

            # Create 3 transactions attached to the same gift ID = 1 and one transaction to each remaining gift.
            total_transactions = 5
            transaction_models = []
            for i in range( 0, total_transactions ):  # pylint: disable=W0612
                transaction_json = get_transaction_dict()
                del transaction_json[ 'id' ]
                if i <= 2:
                    transaction_json[ 'gift_id' ] = 1
                    transaction_json[ 'gift_searchable_id' ] = uuid.UUID( searchable_ids[ 0 ] ).hex
                elif i == 3:
                    transaction_json[ 'gift_id' ] = i
                    transaction_json[ 'gift_searchable_id' ] = uuid.UUID( searchable_ids[ i ] ).hex
                    transaction_json[ 'notes' ] = ''
                else:
                    transaction_json[ 'gift_id' ] = i
                    transaction_json[ 'gift_searchable_id' ] = uuid.UUID( searchable_ids[ i ] ).hex

                transaction_model = TransactionSchema().load( transaction_json ).data
                transaction_models.append( transaction_model )

            database.session.bulk_save_objects( transaction_models )
            database.session.commit()

            # searchable_ids[ 0 ] is gift ID = 1 and will have 3 transactions.
            response = self.test_client.get( url.format( uuid.UUID( searchable_ids[ 1 ] ).hex ), headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 0 )

            # searchable_ids[ 1 ] is gift ID = 2 and will have 0 transactions.
            response = self.test_client.get( url.format( uuid.UUID( searchable_ids[ 1 ] ).hex ), headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 0 )

            # searchable_ids[ 2 ] is gift ID = 3 and will have 1 transaction with note = ''.
            response = self.test_client.get( url.format( uuid.UUID( searchable_ids[ 2 ] ).hex ), headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 0 )

            # searchable_ids[ 3 ] is gift ID = 4 and will have 1 transaction with a note != ''.
            response = self.test_client.get( url.format( uuid.UUID( searchable_ids[ 3 ] ).hex ), headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 1 )
