"""A module for handling the process of building output streams and files."""
import io
from datetime import datetime

from s3_web_storage.web_storage import WebStorage

CSV_FILE_TYPE = 'csv'
FILENAME_PREFIX_TRANSACTION = 'transaction_status_changes_for'

# Using local time for file names stored by Webstorage ( S3 ).
FILENAME_DATETIME = datetime.now().strftime( '%Y_%m_%d' )


def build_flat_bytesio_csv( data, field_names, file_name, save=False ):
    """Build the io.BytesIO() object for CSV output.

    :param data: Data to put in CSV stream.
    :param field_names: Header row of strings.
    :param file_name: Save to this file name.
    :param save: Whether to save to S3.
    :return:
    """

    output = io.BytesIO()
    if field_names:
        output.write( ','.join( field_names ).encode() )
        output.write( '\n'.encode() )
    for transaction in data:
        output.write( ','.join( map( str, transaction ) ).encode() )
        output.write( '\n'.encode() )

    if save:
        file_name = '{}_{}.{}'.format( file_name, FILENAME_DATETIME, CSV_FILE_TYPE )
        metadata = ( 'Transaction Updater', file_name )
        save_csv_file( output, file_name, metadata )

    output.close()
    return file_name


def save_csv_file( file_data, file_name, metadata ):
    """Given the campaign model use its ID to name the file and save the photo to S3.

    :param file_data: CSV stream data to save to S3.
    :param file_name: The file name.
    :param metadata: File metadata for WebStorage.
    """

    # Get the file_type: file_storage.content_type is something like 'image/png'.
    WebStorage.save( file_name, file_data.getvalue(), metadata )
