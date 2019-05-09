"""The module tests various API endpoints to ensure a request is successfully made and valid data returned."""
import json
import unittest

import mock
from flask_api import status

from application.app import create_app
from application.flask_essentials import database
from application.schemas.agent import AgentSchema
from application.schemas.caged_donor import CagedDonorSchema
from tests.helpers.default_dictionaries import get_agent_jsons
from tests.helpers.default_dictionaries import get_caged_donor_dict
from tests.helpers.mock_braintree_objects import mock_generate_braintree_token
from tests.helpers.mock_braintree_objects import mock_init_braintree_credentials
from tests.helpers.mock_jwt_functions import ACCESS_TOKEN
from tests.helpers.mock_webstorage_objects import mock_webstorage_get_bucket_file
from tests.helpers.mock_webstorage_objects import mock_webstorage_init_storage
from tests.helpers.mock_webstorage_objects import mock_webstorage_s3_file_list
from tests.helpers.model_helpers import create_model_list

BRAINTREE_TOKEN = 'braintree_token'


class APIOtherEndpointsTestCase( unittest.TestCase ):
    """This test suite is designed to verify the basic functionality of various API endpoints.

    All endpoints that retrieve data from the database are tested here. These include any calls which are performing
    queries before returning data.

    The endpoints that depend upon the Braintree API need to be mocked and are tested elsewhere.

    python -m unittest discover -v
    python -m unittest -v tests.test_api_other_endpoints.APIOtherEndpointsTestCase
    python -m unittest -v tests.test_api_other_endpoints.APIOtherEndpointsTestCase.test_get_agents
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

    def test_get_agents( self ):
        """Agents API endpoint ( methods = [ GET ] )."""

        with self.app.app_context():
            url = '/donation/agents'

            # Ensure a GET with no saved agents returns 0.
            response = self.test_client.get( url, headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 0 )

            # Create some agents to retrieve.
            agent_models = []
            agent_jsons = get_agent_jsons()
            for agent_json in agent_jsons:
                agent_model = AgentSchema().load( agent_json ).data
                agent_models.append( agent_model )
            database.session.bulk_save_objects( agent_models )
            database.session.commit()

            # Ensure GET returns all agents.
            response = self.test_client.get( url, headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), len( agent_jsons ) )

    @mock.patch(
        'application.controllers.donate.init_braintree_credentials', side_effect=mock_init_braintree_credentials
    )
    @mock.patch(
        'application.controllers.donate.generate_braintree_token', side_effect=mock_generate_braintree_token
    )
    def test_get_token(
            self,
            mock_init_credentials_function,
            mock_generate_token_function
    ):  # pylint: disable=unused-argument
        """Test to check that the endpoint exists ( methods = [ GET ] ).

        The endpoint calls 2 functions that make calls to the BRAINTREE_TOKEN API. These functions are mocked. This
        test basically makes sure that if the credentials are initialized and the token is retrieved it is returned
        when the endpoint is called.
        """

        with self.app.app_context():
            url = '/donation/braintree/get-token'

            # Ensure a GET with no saved agents returns 0.

            response = self.test_client.get( url, headers=self.headers )
            self.assertEqual( json.loads( response.data.decode( 'utf-8' ) ), BRAINTREE_TOKEN )

    def test_caged_donors( self ):
        """Caged donor API ( methods = [ GET ] )."""
        with self.app.app_context():
            url = '/donation/donors/caged'
            # Ensure a GET with no saved caged_donors returns 0.
            response = self.test_client.get( url, headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), 0 )

            # Create some caged_donors to retrieve.
            total_caged_donors = 5
            caged_donor_models = create_model_list( CagedDonorSchema(), get_caged_donor_dict(), total_caged_donors )
            database.session.bulk_save_objects( caged_donor_models )
            database.session.commit()

            # Ensure GET returns all caged_donors.
            response = self.test_client.get( url, headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), total_caged_donors )

    def test_enumerations( self ):
        """Test get enumerations API ( methods = [ GET ] )."""
        with self.app.app_context():
            url = '/donation/enumeration/{}/{}'

            response = self.test_client.get( url.format( 'giftmodel', 'given_to' ), headers=self.headers )
            self.assertGreater( len( json.loads( response.data.decode( 'utf-8' ) ) ), 0 )

            response = self.test_client.get( url.format( 'transactionmodel', 'type' ), headers=self.headers )
            self.assertGreater( len( json.loads( response.data.decode( 'utf-8' ) ) ), 0 )

            response = self.test_client.get( url.format( 'transactionmodel', 'status' ), headers=self.headers )
            self.assertGreater( len( json.loads( response.data.decode( 'utf-8' ) ) ), 0 )

            response = self.test_client.get( url.format( 'agentmodel', 'type' ), headers=self.headers )
            self.assertGreater( len( json.loads( response.data.decode( 'utf-8' ) ) ), 0 )

    def test_heartbeat( self ):
        """Caged donor API ( methods = [ GET ] )."""
        with self.app.app_context():
            url = '/donation/heartbeat'

            # Ensure a GET with no saved caged_donors returns 0.
            response = self.test_client.get( url, headers=self.headers )
            self.assertEqual( response.status_code, status.HTTP_200_OK )

    @mock.patch(
        'application.controllers.file_management.WebStorage.init_storage',
        side_effect=mock_webstorage_init_storage
    )
    @mock.patch(
        'application.controllers.file_management.WebStorage.get_bucket_file',
        side_effect=mock_webstorage_get_bucket_file
    )
    def test_s3_csv_download(
            self,
            mock_init_storage_function,
            mock_get_bucket_file_function
    ):  # pylint: disable=unused-argument
        """Make sure the endpoint is available and raises the proper error if query parameters are wrong."""

        with self.app.app_context():
            url = '/donation/s3/csv/download?bucket={}&path={}&file_name={}&local_path={}'

            bucket = self.app.config[ 'AWS_CSV_FILES_BUCKET' ]
            path = self.app.config[ 'AWS_CSV_FILES_PATH' ]
            file_name = 'test_file_name'
            local_path = 'test_local_path'

            response = self.test_client.get( url.format( bucket, path, file_name, local_path ), headers=self.headers )
            self.assertEqual( response.status_code, status.HTTP_200_OK )

    @mock.patch(
        'application.controllers.file_management.WebStorage.init_storage',
        side_effect=mock_webstorage_init_storage
    )
    @mock.patch(
        'application.controllers.file_management.WebStorage.get_list_of_bucket_files',
        side_effect=mock_webstorage_s3_file_list
    )
    def test_s3_csv_file_list(
            self,
            mock_init_storage_function,
            mock_get_list_of_bucket_files
    ):  # pylint: disable=unused-argument
        """Make sure the endpoint is available and raises the proper error if query parameters are wrong."""

        with self.app.app_context():
            url = '/donation/s3/csv/files?bucket={}&path={}'

            bucket = self.app.config[ 'AWS_CSV_FILES_BUCKET' ]
            path = self.app.config[ 'AWS_CSV_FILES_PATH' ]

            response = self.test_client.get( url.format( bucket, path ), headers=self.headers )
            self.assertEqual( response.status_code, status.HTTP_200_OK )
