"""File management controllers."""
from flask import current_app
from s3_web_storage.web_storage import WebStorage
from sqlalchemy.orm.exc import NoResultFound as SQLAlchemyORMNoResultFoundError

from application.exceptions.exception_file_management import FileManagementIncompleteQueryString
from application.models.campaign import CampaignModel


def get_s3_file_list( query_terms ):
    """Get a file list from the given bucket and path given in the query terms.

    query_terms will look like: donation/s3/download?bucket=nusa-dev-testing&path=apeters/

    :param query_terms: See example in the URL above.
    :return: A list of files in the given bucket at the given path.
    """

    query_term_keys = set( query_terms.keys() )
    not_matching_terms = len( query_term_keys.symmetric_difference( { 'bucket', 'path' } ) )
    if not_matching_terms:
        raise FileManagementIncompleteQueryString

    WebStorage.init_storage( current_app, query_terms[ 'bucket' ][ 'eq' ], query_terms[ 'path' ][ 'eq' ] )
    return WebStorage.get_list_of_bucket_files()


def get_s3_file( query_terms ):
    """Download a file to the users local drive at the path given in the query parameters.

    query_terms will look like:
        donation/s3/download?bucket=nusa-dev-testing&path=apeters/&file_name=dispute.csv&local_path=/tmp/dispute.csv

    :param query_terms: See example in the URL above.
    :return: A file in the bucket downloaded to the given local path.
    """
    query_term_keys = set( query_terms.keys() )
    not_matching_terms = len( query_term_keys.symmetric_difference( { 'bucket', 'path', 'file_name', 'local_path' } ) )
    if not_matching_terms:
        raise FileManagementIncompleteQueryString

    WebStorage.init_storage( current_app, query_terms[ 'bucket' ][ 'eq' ], query_terms[ 'path' ][ 'eq' ] )
    WebStorage.get_bucket_file(
        query_terms[ 'file_name' ][ 'eq' ],
        query_terms[ 'local_path' ][ 'eq' ]
    )


def get_s3_file_path( campaign_id ):
    """Given the argument for the Campiagn ID build the file path to AWS S3.

        :param campaign_id: The CampaignModel ID ( CampaignModel.id ).
        :return: File path to image.
    """

    try:
        campaign_model = CampaignModel.query.filter_by( id=campaign_id ).one()
        file_type = campaign_model.photo_type
    except SQLAlchemyORMNoResultFoundError as error:
        raise error

    WebStorage.init_storage( current_app )
    s3_path = WebStorage.get_s3_path()

    image_file_path = '{}{}.{}'.format( s3_path, campaign_id, file_type )

    return image_file_path
