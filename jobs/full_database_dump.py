"""Generate a full dump of the donate database to a CSV file and upload to AWS S3.

python -c "import jobs.full_database_dump;jobs.full_database_dump.get_cron_for_csv()"
"""
import io
import logging
import os
from datetime import datetime

import pymysql
import requests
from s3_web_storage.web_storage import WebStorage

from application.app import create_app
from application.helpers.general_helper_functions import get_vault_data
from application.helpers.sql_queries import query_transactions_for_csv
# pylint: disable=bare-except
# pylint: disable=no-member
# pylint: disable=invalid-name

# Check for how the application is being run and use that.
# The environment variable is set in the Dockerfile.
app_config_env = os.environ[ 'APP_ENV' ]  # pylint: disable=invalid-name
app = create_app( app_config_env )  # pylint: disable=C0103

WebStorage.init_storage( app, app.config[ 'AWS_CSV_FILES_BUCKET' ], app.config[ 'AWS_CSV_FILES_PATH' ] )

HEADER = [
    'gift_id', 'method_used', 'given_to', 'given_by_user_id', 'originating_agent_name',
    'originating_agent_id', 'searchable_gift_id', 'gift_id', 'reference_number', 'transaction_agent_name',
    'transaction_agent_id', 'transaction_type', 'transaction_status', 'transaction_date',
    'transaction_gross', 'transaction_fee', 'notes'
]

FILE_TYPE = 'csv'
FILE_PREFIX = 'full_database_dump_at'
FILE_DATETIME = datetime.now().strftime( '%Y_%m_%d' )
FILE_NAME = '{}_{}.{}'.format( FILE_PREFIX, FILE_DATETIME, FILE_TYPE )


def get_cron_for_csv():
    """A function to be called as a cron job to retrieve a full diump of the donate database to a CSV."""

    # Open the stream for CSV and write the header.
    output = io.BytesIO()
    output.write( ','.join( HEADER ).encode() )
    output.write( '\n'.encode() )

    logging.info( '' )
    logging.info( '1. Open the production DB connection.' )

    # Handle vault tokens.
    vault = get_vault_data( app.config[ 'VAULT_URL' ], app.config[ 'VAULT_TOKEN' ], app.config[ 'VAULT_SECRET' ] )

    # Create the database connection.
    dump_conn = pymysql.connect(
        host=app.config[ 'DUMP_SQLALCHEMY_HOST' ],
        port=int( app.config[ 'DUMP_SQLALCHEMY_PORT' ] ),
        user=vault[ 'data' ][ 'username' ],
        passwd=vault[ 'data' ][ 'password' ],
        db=app.config[ 'DUMP_SQLALCHEMY_DB' ]
    )

    logging.info( '2. Get the data.' )

    # Get the MySQL query to extract data from the database.
    sql_query = query_transactions_for_csv()

    # Get the cursor and perform query, with the MySQL equivalent of nolock on the database.
    dump_cursor = dump_conn.cursor()
    with dump_cursor as cursor:
        cursor.execute( 'SET SESSION TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;' )
        cursor.execute( sql_query )
        rows = list( cursor )
        cursor.execute( 'SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ;' )

    logging.info( '3. Write the data.' )

    # Write the query data to the output stream.
    for row in rows:
        output.write( ','.join( map( str, row ) ).encode() )
        output.write( '\n'.encode() )

    logging.info( '4. Save the data.' )

    # Save the data to AS S3 and get the URL.
    metadata = ( 'Transaction Updater', FILE_NAME )
    WebStorage.save( FILE_NAME, output.getvalue(), metadata )
    url = WebStorage.generate_presigned_url(
        app.config[ 'AWS_CSV_FILES_BUCKET' ],
        app.config[ 'AWS_CSV_FILES_PATH' ] + FILE_NAME
    )

    # Send a notification email to the group.
    email = app.config[ 'STATISTICS_GROUP_EMAIL' ]
    data = {
        'email': email,
        'urls': url
    }
    ultsys_email_api_key = app.config[ 'ULTSYS_EMAIL_API_KEY' ]
    ultsys_email_url = app.config[ 'ULTSYS_EMAIL_URL' ]
    headers = { 'content-type': 'application/json', 'X-Temporary-Service-Auth': ultsys_email_api_key }
    requests.post(
        ultsys_email_url,
        params=data,
        headers=headers
    )

    logging.info( url )
