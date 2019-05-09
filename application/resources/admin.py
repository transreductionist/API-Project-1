"""Resources entry point for initiating administrative functions."""
from flask import request
from flask_api import status
from nusa_jwt_auth import get_jwt_claims
from nusa_jwt_auth.restful import AdminResource

from application.controllers.admin import admin_get_braintree_sale_status
from application.controllers.admin import admin_correct_gift
from application.controllers.admin import admin_record_bounced_check
from application.controllers.admin import admin_refund_transaction
from application.controllers.admin import admin_void_transaction
from application.exceptions.exception_jwt import JWTRequestError
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use


class GetBraintreeSaleStatus( AdminResource ):
    """Flask-RESTful resource endpoint for getting the status of a Braintree sale.."""

    def get( self, transaction_id ):
        """GET method to determine the status of a Braintree sale.

        : param searchable_id : The gift searchable ID to find the status os.
        :return: Braintree sale status.
        """

        braintree_status = admin_get_braintree_sale_status( transaction_id )
        if braintree_status:
            return braintree_status, status.HTTP_200_OK
        return None, status.HTTP_500_INTERNAL_SERVER_ERROR


class DonateAdminRecordBouncedCheck( AdminResource ):
    """Flask-RESTful resource endpoint for recording bounced checks."""

    def post( self ):
        """POST method to record a bounced check.

        :return: HTTP status code.
        """

        # Authenticate the admin user.
        payload = request.json
        try:
            payload[ 'user_id' ] = get_jwt_claims()[ 'ultsys_id' ]
        except KeyError:
            raise JWTRequestError()

        if admin_record_bounced_check( payload ):
            return None, status.HTTP_200_OK
        return None, status.HTTP_500_INTERNAL_SERVER_ERROR


class DonateAdminRefund( AdminResource ):
    """Flask-RESTful resource endpoint for refunding gifts."""

    def post( self ):
        """POST method to record an administrative refund on a transaction which is in settling or settled.

        :return: HTTP status code.
        """

        # Authenticate the admin user.
        payload = request.json
        try:
            payload[ 'user_id' ] = get_jwt_claims()[ 'ultsys_id' ]
        except KeyError:
            raise JWTRequestError()

        if admin_refund_transaction( payload ):
            return None, status.HTTP_200_OK
        return None, status.HTTP_500_INTERNAL_SERVER_ERROR


class DonateAdminCorrection( AdminResource ):
    """Flask-RESTful resource endpoint for correcting and/or reallocating gifts."""

    def post( self ):
        """POST method to correct and/or reallocate a gift.

         payload = {
              "gift": {
                  "reallocate_to": "NERF"
              },
              "transaction": {
                  "gift_searchable_id": "6AE03D8EA2DC48E8874F0A76A1C43D5F",
                  "reference_number": null,
                  "gross_gift_amount": "1000.00",
                  "notes": "An online donation to test receipt sent email."
              },
              "user": {
                  "user_id": 1
              }
        }

        The gift may be reallocated to a different plan, and in this case if there is a subscription the  plan ID
        is changed.

        Grab the agent Ultsys ID from the JWT token and place it in the payload.

        :return: HTTP status code.
        """

        # Authenticate the admin user.
        payload = request.json
        try:
            payload[ 'agent_ultsys_id' ] = get_jwt_claims()[ 'ultsys_id' ]
        except KeyError:
            raise JWTRequestError()

        if admin_correct_gift( payload ):
            return None, status.HTTP_200_OK
        return None, status.HTTP_500_INTERNAL_SERVER_ERROR


class DonateAdminVoid( AdminResource ):
    """Flask-RESTful resource endpoint for voiding gifts."""

    def post( self ):
        """POST method to record an administrative refund on a transaction which is in submitted for settlement.

        :return: HTTP status code.
        """

        # Authenticate the admin user.
        payload = request.json
        try:
            payload[ 'user_id' ] = get_jwt_claims()[ 'ultsys_id' ]
        except KeyError:
            raise JWTRequestError()

        if admin_void_transaction( payload ):
            return None, status.HTTP_200_OK
        return None, status.HTTP_500_INTERNAL_SERVER_ERROR
