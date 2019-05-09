"""Resource entry point for the Paypal ETL endpoints."""
from flask import request
from flask_api import status
from nusa_jwt_auth import get_jwt_claims
from nusa_jwt_auth.restful import AdminResource

from application.controllers.paypal_etl import manage_paypal_etl
from application.exceptions.exception_jwt import JWTRequestError
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use


class PaypalETL( AdminResource ):
    """Flask-RESTful resource endpoints for Paypal ETL"""

    def post( self ):
        """Manage the PayPal ETL CSV upload request by updating the models."""

        # Authenticate the admin user.
        try:
            request.form[ 'admin_user_id' ] = get_jwt_claims()[ 'ultsys_id' ]
        except KeyError:
            raise JWTRequestError()

        result = manage_paypal_etl( request )
        if result:
            return None, status.HTTP_200_OK

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR
