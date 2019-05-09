"""The Resources entry point for file management, e.g AWS S3."""
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use
from flask import request
from flask_api import status
from nusa_filter_param_parser.nusa_filter_param_parser import build_filter_from_request_args
from nusa_jwt_auth.restful import AdminResource

from application.controllers.file_management import get_s3_file
from application.controllers.file_management import get_s3_file_list
from application.controllers.file_management import get_s3_file_path


class GetS3FileList( AdminResource ):
    """Flask-RESTful resource endpoint to get a list of files in a bucket given a path."""

    def get( self ):
        """Endpoint to retrieve a list of files in a given bucket and path.

        example query_terms: donation/s3/download?bucket=nusa-dev-testing&path=apeters/
        """

        query_terms = build_filter_from_request_args( request.args )
        return get_s3_file_list( query_terms ), status.HTTP_200_OK


class GetS3File( AdminResource ):
    """Flask-RESTful resource endpoint to download a file to the users local drive from a bucket given a path."""

    def get( self ):
        """Simple endpoint to download a file to the users local disk at local_path.

        example query_terms:
            donation/s3/download?bucket=?
                nusa-dev-testing&path=apeters/&file_name=dispute.csv&local_path=/tmp/dispute.csv
        """

        query_terms = build_filter_from_request_args( request.args )
        get_s3_file( query_terms )
        return None, status.HTTP_200_OK


class GetS3FilePath( AdminResource ):
    """Flask-RESTful resource endpoints to get an enumeration on a model."""

    def get( self, campaign_id ):
        """Retrieve the file path for a Campaign image on AWS S3 given its ID.

        :param campaign_id: The CampaignModel ID ( CampaignModel.id ).
        :return: File path to the image.
        """

        return get_s3_file_path( campaign_id ), status.HTTP_200_OK
