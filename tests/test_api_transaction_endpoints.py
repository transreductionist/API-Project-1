"""The module tests each Transaction API endpoint to ensure a request is successfully made and valid data returned."""
import json
import unittest
import uuid
from decimal import Decimal

import mock

from application.app import create_app
from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from application.schemas.agent import AgentSchema
from application.schemas.gift import GiftModel
from application.schemas.gift import GiftSchema
from application.schemas.transaction import TransactionSchema
from tests.helpers.default_dictionaries import get_agent_dict
from tests.helpers.default_dictionaries import get_gift_dict
from tests.helpers.default_dictionaries import get_gift_searchable_ids
from tests.helpers.default_dictionaries import get_transaction_dict
from tests.helpers.mock_jwt_functions import ACCESS_TOKEN
from tests.helpers.mock_webstorage_objects import mock_generate_presigned_url
from tests.helpers.mock_webstorage_objects import mock_webstorage_init_storage
from tests.helpers.mock_webstorage_objects import mock_webstorage_save
from tests.helpers.model_helpers import create_model_list


class APITransactionEndpointsTestCase( unittest.TestCase ):
    """This test suite is designed to verify the basic functionality of the Transaction API endpoints.

    All endpoints that retrieve data from the database are tested here. These include any calls which are performing
    queries before returning data.

    The endpoints that depend upon the Braintree API need to be mocked and are tested elsewhere.

    python -m unittest discover -v
    python -m unittest -v tests.test_api_transaction_endpoints.APITransactionEndpointsTestCase
    python -m unittest -v tests.test_api_transaction_endpoints.APITransactionEndpointsTestCase.test_get_transactions_get
    """

    def setUp( self ):
        self.app = create_app( 'TEST' )
        self.app.testing = True
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

    def test_get_transactions_get( self ):
        """Transaction endpoint with one ID retrieves the transaction ( methods = [ GET ] )."""

        with self.app.app_context():
            url = '/donation/transactions/{}'
            # Ensure a GET to with no database entries returns nothing.
            response = self.test_client.get( url.format( 2 ), headers=self.headers )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

            # Create a set of transactions.
            total_transactions = 5
            transaction_models = create_model_list(
                TransactionSchema(),
                get_transaction_dict( { 'gift_id': 1 } ),
                total_transactions
            )

            database.session.bulk_save_objects( transaction_models )
            database.session.commit()

            # Ensure a GET with one ID returns the correct transaction.
            response = self.test_client.get( url.format( 2 ), headers=self.headers )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( data_returned[ 'id' ], 2 )

    def test_get_transactions_post( self ):
        """Transaction endpoint with many ID's retrieves all the transaction ( methods = [ GET, POST ] )."""

        with self.app.app_context():
            url = '/donation/transactions'

            # Ensure a GET with no database entries returns nothing.
            response = self.test_client.get( url, headers=self.headers )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

            # Ensure a POST with no database entries returns nothing.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'transaction_ids': [ 2 ] } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

    def test_get_transactions_by_amount( self ):
        """Retrieves all transactions with amounts ( <=, <= && <= ) specified amounts ( methods = [ POST ] )."""

        with self.app.app_context():
            url = '/donation/transactions/gross-gift-amount'

            # Ensure that with no database entries endpoint returns nothing.
            gross_gift_amount = '10.00'
            response = self.test_client.post(
                url,
                data=json.dumps( { 'gross_gift_amount': gross_gift_amount } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

            # Create a set of transactions for gross gift amounts.
            # Here are the amounts: {
            #     transaction 0: 10.00,
            #     transaction 1: 11.00,
            #     transaction 2: 12.00,
            #     transaction 3: 13.00,
            #     transaction 4: 14.00
            # }

            total_transactions = 5
            transaction_models = []
            gross_gift_amount = Decimal( 10.00 )

            i = 1
            while i <= total_transactions:
                transaction_payload = {
                    'gift_id': i,
                    'gross_gift_amount': str( gross_gift_amount )
                }
                transaction_model = from_json(
                    TransactionSchema(),
                    get_transaction_dict( transaction_payload ),
                    create=True
                )
                transaction_models.append( transaction_model.data )
                gross_gift_amount = Decimal( 10.00 + i )
                i += 1

            database.session.bulk_save_objects( transaction_models )
            database.session.commit()

            # A large amount should bring back no transactions.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'gross_gift_amount': '100.00' } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 0 )

            # A small amount should bring back all transactions.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'gross_gift_amount': '0.00' } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), total_transactions )

            # A range should bring back the correct number of transactions.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'gross_gift_amount': [ '11.00', '13.00' ] } ),
                content_type='application/json',
                headers=self.headers
            )
            data_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( len( data_returned ), 3 )

    def test_get_transactions_by_gift( self ):
        """Retrieves all transactions with a specified gift searchable_id ( methods = [ GET ] )."""

        with self.app.app_context():
            # The parameter is for the searchable_id.
            url = '/donation/gifts/{}/transactions'

            # Create 3 gifts to attach transactions to.
            # Create each gift with a reproducible UUID.
            total_gifts = 5
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

            # Create 3 transactions attached to the same gift ID = 1, one transaction to 4 and none on 5.
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
                else:
                    transaction_json[ 'gift_id' ] = i
                    transaction_json[ 'gift_searchable_id' ] = uuid.UUID( searchable_ids[ i ] ).hex

                transaction_model = TransactionSchema().load( transaction_json ).data
                transaction_models.append( transaction_model )

            database.session.bulk_save_objects( transaction_models )
            database.session.commit()

            # searchable_ids[ 0 ] is gift ID = 1 and will have 3 transactions.
            response = self.test_client.get( url.format( uuid.UUID( searchable_ids[ 0 ] ).hex ), headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 3 )

            # searchable_ids[ 2 ] is gift ID = 3 and will have 1 transactions.
            response = self.test_client.get( url.format( uuid.UUID( searchable_ids[ 2 ] ).hex ), headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 1 )

            # searchable_ids[ 4 ] is gift ID = 5 and will have 0 transactions.
            response = self.test_client.get( url.format( uuid.UUID( searchable_ids[ 4 ] ).hex ), headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 0 )

    def test_get_transactions_by_gifts( self ):
        """Retrieves all transactions or those in a list of gift searchable_id's ( methods = [ GET, POST ] )."""

        with self.app.app_context():
            # The parameter is for the searchable_id.
            url = '/donation/gifts/transactions'

            # Create 3 gifts to attach transactions to.
            # Create each gift with a reproducible UUID.
            total_gifts = 5
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

            # Create 3 transactions attached to the same gift ID = 1, one transaction to 4 and none on 5.
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
                else:
                    transaction_json[ 'gift_id' ] = i
                    transaction_json[ 'gift_searchable_id' ] = uuid.UUID( searchable_ids[ i ] ).hex

                transaction_model = TransactionSchema().load( transaction_json ).data
                transaction_models.append( transaction_model )

            database.session.bulk_save_objects( transaction_models )
            database.session.commit()

            # Get all transactions in the database.
            response = self.test_client.get( url, headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 5 )

            # searchable_ids[ 0 ] is gift ID = 1 and will have 3 transactions: test string searchable ID.
            response = self.test_client.post(
                url,
                data=json.dumps( { 'searchable_ids': uuid.UUID( searchable_ids[ 0 ] ).hex } ),
                content_type='application/json',
                headers=self.headers
            )

            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 3 )

            # Gift ID = 1 and 2 and will have a total of 4 transactions: test list of searchable ID's.
            response = self.test_client.post(
                url,
                data=json.dumps(
                    {
                        'searchable_ids':
                            [ uuid.UUID( searchable_ids[ 0 ] ).hex, uuid.UUID( searchable_ids[ 2 ] ).hex ]
                    }
                ),
                content_type='application/json',
                headers=self.headers
            )

            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 4 )

    def test_build_transaction( self ):
        """Transactions endpoint to add a transaction to a gift with searchable_id ( methods = [ POST ] )."""

        with self.app.app_context():
            # Parameter in URL is for a searchable_id_prefix.
            url = '/donation/gift/transaction'

            agent_dict = get_agent_dict( { 'name': 'Aaron Peters', 'user_id': 3255162, 'type': 'Staff Member' } )
            agent_model = from_json( AgentSchema(), agent_dict, create=True )
            database.session.add( agent_model.data )

            # Create a gift to attach a transaction to.
            gift_json = get_gift_dict()
            del gift_json[ 'id' ]
            gift_json[ 'searchable_id' ] = uuid.uuid4()
            gift_model = GiftSchema().load( gift_json ).data
            database.session.add( gift_model )
            database.session.commit()

            gift = GiftModel.query.all()[ 0 ]

            # Ensure no transactions currently on gift.
            self.assertEqual( len( gift.transactions ), 0 )

            new_transaction = get_transaction_dict(
                {
                    'gift_searchable_id': gift_json[ 'searchable_id' ].hex,
                    'enacted_by_agent_id': None
                }
            )

            self.test_client.post(
                url,
                data=json.dumps( new_transaction ),
                content_type='application/json',
                headers=self.headers
            )

            # Ensure the new transactions is now on the gift.
            self.assertEqual( len( gift.transactions ), 1 )
            self.assertEqual( gift.transactions[ 0 ].gift_searchable_id.hex, gift_json[ 'searchable_id' ].hex )

    @mock.patch(
        'application.controllers.transaction.WebStorage.init_storage',
        side_effect=mock_webstorage_init_storage
    )
    @mock.patch(
        'application.controllers.transaction.WebStorage.generate_presigned_url',
        side_effect=mock_generate_presigned_url
    )
    @mock.patch(
        'application.helpers.build_output_file.WebStorage.save',
        side_effect=mock_webstorage_save
    )
    def test_get_transactions_for_csv(
            self,
            mock_init_storage_function,
            mock_web_storage_save,
            mock_gen_presigned_url_function
    ):  # pylint: disable=unused-argument
        """Retrieves all transactions to dump to the CSV file methods = [ GET ] )."""

        with self.app.app_context():
            # The parameter is for the searchable_id.
            url = '/donation/transactions/csv'

            self.test_client.get( url, headers=self.headers )
