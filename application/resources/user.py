"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use
from flask import request
from flask_api import status
from nusa_jwt_auth.restful import AdminResource

from application.controllers.user import ultsys_user


class UltsysUser( AdminResource ):
    """Flask-RESTful resource endpoints for Drupal/Ultsys user services."""

    def get( self ):
        """Simple endpoint to handle Ultsys user database calls."""
        response = ultsys_user( request.args )
        if response or response == []:
            return response, status.HTTP_200_OK

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR

    def put( self ):
        """Simple endpoint to handle user update in Ultsys."""
        response = ultsys_user( request.json )
        if response or response == []:
            return response, status.HTTP_200_OK

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR

    def post( self ):
        """Simple endpoint to handle creation of Ultsys user."""
        response = ultsys_user( request.json )
        if response or response == []:
            return response, status.HTTP_200_OK

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR
