"""Resource entry point to handle the business logic for the endpoint."""
from flask import request
from flask_api import status
from nusa_jwt_auth.restful import AdminResource

from application.controllers.front_end_caging import build_ultsys_user
from application.controllers.front_end_caging import update_caged_donor
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use


class CageDonorAsUltsysUser( AdminResource ):
    """Flask-RESTful resource endpoints to handle caged donors."""

    def post( self ):
        """Create new Ultsys user using the caged donor ( updated with payload ), then deleting caged donor."""

        payload = request.json
        payload[ 'ultsys_user_id' ] = None
        response = build_ultsys_user( payload )
        if response:
            return response, status.HTTP_200_OK

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR

    def put( self ):
        """Update Ultsys user assigned using the caged donor ( updated with payload ), then deleting caged donor."""

        payload = request.json
        response = build_ultsys_user( payload )
        if response:
            return response, status.HTTP_200_OK

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR


class CageDonorUpdate( AdminResource ):
    """Flask-RESTful resource endpoints to update a caged donor in the table."""

    def put( self ):
        """Update the caged donor address."""

        response = update_caged_donor( request.json )
        if response:
            return None, status.HTTP_200_OK

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR
