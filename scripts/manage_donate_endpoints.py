"""The following script will aid in the management of the API endpoints.

python -c "import scripts.manage_donate_endpoints;scripts.manage_donate_endpoints.paypal_etl()"
python -c "import scripts.manage_donate_endpoints;scripts.manage_donate_endpoints.create_campaign()"
"""
import json
import os
from datetime import datetime

import requests
from werkzeug.datastructures import FileStorage

from application.app import create_app
from tests.helpers.mock_jwt_functions import ACCESS_TOKEN

app = create_app( 'DEV' )  # pylint: disable=C0103

DATE_IN_UTC = datetime.utcnow()
DATE_IN_UTC = DATE_IN_UTC.strftime( '%Y-%m-%d %H:%M:%S' )

SCRIPT_DIR = os.path.dirname( __file__ )

PNG_FILE_NAME = 'gear_wheel.png'
PNG_NAME = 'Gear'
REL_PNG_FILE_PATH = 'tests/resources/images/{}'.format( PNG_FILE_NAME )
PNG_FILE_PATH = os.path.join( SCRIPT_DIR, '..', REL_PNG_FILE_PATH )

CSV_FILE_NAME = 'paypal_action_test.csv'
REL_CSV_FILE_PATH = '{}'.format( CSV_FILE_NAME )
CSV_FILE_PATH = os.path.join( SCRIPT_DIR, REL_CSV_FILE_PATH )
HEADERS = { 'Authorization': 'Bearer {}'.format( ACCESS_TOKEN ) }


def paypal_etl():
    """Build payload and call PayPal ETL endpoint with multipart/form-data."""

    # Use a URL with the application running in a virtual environment.
    # Alternatively, use: curl -v -F admin_user_id=7041 -F upload=@paypal_etl_large.csv
    #     http://donation-apeters.numbersusa.internal/donation
    url = 'http://donation-apeters.numbersusa.internal/donation/paypal-etl'

    form_data = {
        'admin_user_id': 7041
    }

    file = {
        'path': CSV_FILE_PATH,
        'name': CSV_FILE_NAME,
        'content_type': 'text/csv'
    }

    with app.app_context():
        post_multipart_form( url, form_data, file )


def create_campaign():
    """Build payload call the crate campaign endpoint with multipart/form-data."""

    # Use a URL with the application running in a virtual environment.
    # Alternatively, use: curl -v -F admin_user_id=7041 -F upload=@paypal_etl_large.csv
    #     http://donation-apeters.numbersusa.internal/donation
    url = 'http://donation-apeters.numbersusa.internal/donation/campaigns'

    form_data = {
        'id': None,
        'name': 'Red, White, and Blue',
        'description': 'A great campaign!',
        'date_from_utc': DATE_IN_UTC,
        'date_to_utc': DATE_IN_UTC,
        'message': 'Message',
        'photo_type': 'png',
        'video_name': 'Gumballs',
        'video_url': 'free_videos.com',
        'background': 1,
        'is_active': 1,
        'is_default': 1
    }

    amounts = [
        { 'amount': '10.00', 'weight': '0', 'campaign_id': '1' },
        { 'amount': '11.00', 'weight': '1', 'campaign_id': '1' },
        { 'amount': '12.00', 'weight': '2', 'campaign_id': '1' },
        { 'amount': '20.00', 'weight': '0', 'campaign_id': '2' },
        { 'amount': '21.00', 'weight': '1', 'campaign_id': '2' },
        { 'amount': '22.00', 'weight': '2', 'campaign_id': '2' },
    ]

    form_data[ 'amounts' ] = json.dumps( amounts )

    file = {
        'path': PNG_FILE_PATH,
        'name': PNG_FILE_NAME,
        'content_type': 'image/png'
    }

    with app.app_context():
        post_multipart_form( url, form_data, file )


def post_multipart_form( url, form_data, file ):
    """Post the multipart/form. Must be called within an app_context()"""

    with open( file[ 'path' ], 'rb' ) as file_pointer:
        png_file_storage = FileStorage(
            stream=file_pointer,
            filename=file[ 'name' ],
            content_type=file[ 'content_type' ]
        )

        files = { "file": ( png_file_storage.filename, png_file_storage.stream, png_file_storage.mimetype ) }

        response = requests.post(
            url,
            data=form_data,
            files=files,
            headers=HEADERS
        )
        print( 'response.status_code: {}'.format( response.status_code ) )
