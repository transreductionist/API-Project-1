"""The module tests each Campaign API endpoint to ensure a request is successfully made and valid data returned."""
import json
import os
import unittest
from datetime import datetime
from decimal import Decimal

import mock
from flask_api import status
from werkzeug.datastructures import FileStorage

from application.app import create_app
from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from application.models.campaign import CampaignAmountsModel
from application.models.campaign import CampaignModel
from application.schemas.campaign import CampaignAmountsSchema
from application.schemas.campaign import CampaignSchema
from tests.helpers.default_dictionaries import get_campaign_amount_jsons
from tests.helpers.default_dictionaries import get_campaign_dict
from tests.helpers.default_dictionaries import get_update_campaign_dict
from tests.helpers.mock_jwt_functions import ACCESS_TOKEN
from tests.helpers.mock_webstorage_objects import mock_webstorage_delete
from tests.helpers.mock_webstorage_objects import mock_webstorage_init_storage
from tests.helpers.mock_webstorage_objects import mock_webstorage_save
from tests.helpers.model_helpers import create_model_list

PNG_FILE_NAME = 'gear_wheel.png'
PNG_NAME = 'Gear'

JPG_FILE_NAME = 'penguins.jpg'
JPG_NAME = 'Penguins'

TEST_DIR = os.path.dirname( __file__ )
REL_PNG_FILE_PATH = 'resources/images/{}'.format( PNG_FILE_NAME )
PNG_FILE_PATH = os.path.join( TEST_DIR, REL_PNG_FILE_PATH )

REL_JPG_FILE_PATH = 'resources/images/{}'.format( JPG_FILE_NAME )
JPG_FILE_PATH = os.path.join( TEST_DIR, REL_JPG_FILE_PATH )

MODEL_DATETIME_STR_FORMAT = '%Y-%m-%d %H:%M:%S'


class APICampaignEndpointsTestCase( unittest.TestCase ):
    """This test suite is designed to verify the basic functionality of the API Campaign endpoints.

    python -m unittest discover -v
    python -m unittest -v tests.test_api_campaign_endpoints.APICampaignEndpointsTestCase
    python -m unittest -v tests.test_api_campaign_endpoints.APICampaignEndpointsTestCase.test_get_campaign
    """

    def setUp( self ):
        self.app = create_app( 'TEST' )
        self.app.testing = True
        self.test_client = self.app.test_client()
        self.access_token = ACCESS_TOKEN
        self.headers = {
            'Content-Type': 'multipart/form-data',
            'Authorization': 'Bearer {}'.format( self.access_token ) }
        with self.app.app_context():
            database.reflect()
            database.drop_all()
            database.create_all()

    def tearDown( self ):
        with self.app.app_context():
            database.session.commit()
            database.session.close()

    def test_campaigns_active( self ):
        """Retrieve all active or inactive Campaigns API ( methods = [ GET ] )."""
        with self.app.app_context():
            url = '/donation/campaigns/active/1'

            total_active_campaigns = 3
            campaign_models = create_model_list(
                CampaignSchema(), get_campaign_dict( { 'is_active': 1 } ), total_active_campaigns
            )
            database.session.bulk_save_objects( campaign_models )

            total_inactive_campaigns = 2
            campaign_models = create_model_list(
                CampaignSchema(), get_campaign_dict( { 'is_active': 0 } ), total_inactive_campaigns
            )
            database.session.bulk_save_objects( campaign_models )

            database.session.commit()

            response = self.test_client.get( url, headers=self.headers )
            self.assertEqual( len( json.loads( response.data.decode( 'utf-8' ) ) ), total_active_campaigns )

    def test_campaigns_default( self ):
        """Retrieve all default or not default Campaigns API ( methods = [ GET ] )."""
        with self.app.app_context():
            url = '/donation/campaigns/default/1'

            total_default_campaigns = 1
            campaign_models = create_model_list(
                CampaignSchema(), get_campaign_dict( { 'is_default': 1 } ), total_default_campaigns
            )
            database.session.bulk_save_objects( campaign_models )

            total_not_default_campaigns = 2
            campaign_models = create_model_list(
                CampaignSchema(), get_campaign_dict( { 'is_default': 0 } ), total_not_default_campaigns
            )

            database.session.bulk_save_objects( campaign_models )
            database.session.commit()

            response = self.test_client.get( url, headers=self.headers )
            self.assertEqual( json.loads( response.data.decode( 'utf-8' ) )[ 'is_default' ], 1 )

    def test_get_campaign( self ):
        """Retrieve a Campaign given the ID ( methods = [ GET ] )."""
        with self.app.app_context():
            url = '/donation/campaigns/2'

            total_campaigns = 4
            campaign_models = create_model_list(
                CampaignSchema(), get_campaign_dict(), total_campaigns
            )

            database.session.bulk_save_objects( campaign_models )
            database.session.commit()

            response = self.test_client.get( url, headers=self.headers )
            campaign_returned = json.loads( response.data.decode( 'utf-8' ) )
            self.assertEqual( campaign_returned[ 'id' ], 2 )

    def test_get_campaign_amounts( self ):
        """Retrieve the Campaign amounts given its ID ( methods = [ GET ] )."""
        with self.app.app_context():
            url = '/donation/campaigns/2/amounts'

            # Endpoint will check to see that the campaign exists before retrieving amounts and so create a few.
            total_campaigns = 4
            campaign_models = create_model_list(
                CampaignSchema(), get_campaign_dict(), total_campaigns
            )

            database.session.bulk_save_objects( campaign_models )

            campaign_amounts_dict = get_campaign_amount_jsons()
            campaign_amount_models = [ ]
            for amount in campaign_amounts_dict:
                campaign_amount_models.append( from_json( CampaignAmountsSchema(), amount ).data )

            database.session.bulk_save_objects( campaign_amount_models )
            database.session.commit()

            response = self.test_client.get( url, headers=self.headers )
            amounts_returned = json.loads( response.data.decode( 'utf-8' ) )

            self.assertEqual( len( amounts_returned ), 3 )

    @mock.patch( 'application.helpers.campaign.WebStorage.init_storage', side_effect=mock_webstorage_init_storage )
    @mock.patch( 'application.helpers.campaign.WebStorage.save', side_effect=mock_webstorage_save )
    def test_create_campaign(
            self,
            mock_init_storage_function,
            mock_save_function
    ):  # pylint: disable=unused-argument
        """Create a new Campaign ( methods = [ POST ] )."""
        with self.app.app_context():

            form_data = get_campaign_dict()

            amounts = get_campaign_amount_jsons()[ 0:3 ]
            form_data[ 'amounts' ] = json.dumps( amounts )

            with open( PNG_FILE_PATH, 'rb' ) as file_pointer:
                png_file_storage = FileStorage(
                    stream=file_pointer,
                    filename=PNG_FILE_NAME,
                    content_type='image/png'
                )
                form_data[ 'campaign_photo' ] = png_file_storage
                response = self.test_client.post(
                    '/donation/campaigns',
                    data=form_data,
                    headers=self.headers
                )
                self.assertEqual( response.status_code, status.HTTP_200_OK )

            campaign_model = CampaignModel.query.filter_by( id=1 ).one()

            self.assertEqual( campaign_model.name, form_data[ 'name' ] )
            self.assertEqual( campaign_model.description, form_data[ 'description' ] )

            self.assertEqual(
                campaign_model.date_from_utc,
                datetime.strptime( form_data[ 'date_from_utc' ], MODEL_DATETIME_STR_FORMAT )
            )
            self.assertEqual(
                campaign_model.date_to_utc,
                datetime.strptime( form_data[ 'date_to_utc' ], MODEL_DATETIME_STR_FORMAT )
            )

            self.assertEqual( campaign_model.name, form_data[ 'name' ] )
            self.assertEqual( campaign_model.message, form_data[ 'message' ] )
            self.assertEqual( campaign_model.photo_type, form_data[ 'photo_type' ] )
            self.assertEqual( campaign_model.background, int( form_data[ 'background' ] ) )
            self.assertEqual( campaign_model.video_name, form_data[ 'video_name' ] )
            self.assertEqual( campaign_model.video_url, form_data[ 'video_url' ] )
            self.assertEqual( campaign_model.is_active, int( form_data[ 'is_active' ] ) )
            self.assertEqual( campaign_model.is_default, int( form_data[ 'is_default' ] ) )

            campaign_amount_models = CampaignAmountsModel.query.all()
            for index, campaign_amount_model in enumerate( campaign_amount_models ):
                self.assertEqual( campaign_amount_model.amount, Decimal( amounts[ index ][ 'amount' ] ) )
                self.assertEqual( campaign_amount_model.weight, int( amounts[ index ][ 'weight' ] ) )
                self.assertEqual( campaign_amount_model.campaign_id, int( amounts[ index ][ 'campaign_id' ] ) )

    @mock.patch( 'application.helpers.campaign.WebStorage.init_storage', side_effect=mock_webstorage_init_storage )
    @mock.patch( 'application.helpers.campaign.WebStorage.save', side_effect=mock_webstorage_save )
    @mock.patch( 'application.helpers.campaign.WebStorage.delete', side_effect=mock_webstorage_delete )
    def test_update_campaign_with_image(
            self,
            mock_init_storage_function,
            mock_save_function,
            mock_delete_function
    ):  # pylint: disable=unused-argument, too-many-arguments
        """Update an image on the Campaign ( methods = [ POST ] )."""
        with self.app.app_context():

            amounts = get_campaign_amount_jsons()[ 0:3 ]

            # Get the model that will have some, but not all, fields updated.
            campaign_model = from_json( CampaignSchema(), get_campaign_dict() ).data

            database.session.add( campaign_model )

            amount_models = [ from_json( CampaignAmountsSchema(), amount ).data for amount in amounts ]
            database.session.bulk_save_objects( amount_models )

            database.session.commit()

            form_data = get_update_campaign_dict( { 'id': 1, 'photo_type': 'jpeg' } )
            form_data[ 'amounts' ] = json.dumps( amounts[ 0:1 ] )

            response = self.get_response( '/donation/campaigns', form_data )

            self.assertEqual( response.status_code, status.HTTP_200_OK )

            campaign_model_updated = CampaignModel.query.filter_by( id=1 ).one()

            # Make sure the fields that are to be updated actually get updated.
            self.assertEqual( campaign_model_updated.description, form_data[ 'description' ] )
            self.assertEqual( campaign_model_updated.message, form_data[ 'message' ] )
            self.assertEqual( campaign_model_updated.photo_type, form_data[ 'photo_type' ] )
            self.assertEqual( campaign_model_updated.background, int( form_data[ 'background' ] ) )

            # Make sure the fields that were not updated don't change.
            self.assertEqual( campaign_model.name, campaign_model_updated.name )
            self.assertEqual( campaign_model.date_from_utc, campaign_model_updated.date_from_utc )
            self.assertEqual( campaign_model.date_to_utc, campaign_model_updated.date_to_utc )
            self.assertEqual( campaign_model.video_name, campaign_model_updated.video_name )
            self.assertEqual( campaign_model.video_url, campaign_model_updated.video_url )
            self.assertEqual( campaign_model.is_active, campaign_model_updated.is_active )
            self.assertEqual( campaign_model.is_default, campaign_model_updated.is_default )

            for index, campaign_amount_model in enumerate( CampaignAmountsModel.query.all() ):
                self.assertEqual( campaign_amount_model.amount, Decimal( amounts[ index ][ 'amount' ] ) )
                self.assertEqual( campaign_amount_model.weight, int( amounts[ index ][ 'weight' ] ) )
                self.assertEqual( campaign_amount_model.campaign_id, int( amounts[ index ][ 'campaign_id' ] ) )

    def get_response( self, url, form_data ):
        """Helper to get a request with a file"""

        with open( JPG_FILE_PATH, 'rb' ) as file_pointer:
            jpg_file_storage = FileStorage(
                stream=file_pointer,
                filename=JPG_FILE_NAME,
                content_type='image/jpeg'
            )
            form_data[ 'campaign_photo' ] = jpg_file_storage
            response = self.test_client.put(
                url,
                data=form_data,
                content_type='multipart/form-data',
                headers=self.headers
            )
            return response
