"""Resources entry point to make a Braintree sale."""
from flask import request
from nusa_jwt_auth.restful import AdminResource

from application.controllers.reprocess_queued_donors import reprocess_queued_donors
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use


class DonateReprocessQueuedDonors( AdminResource ):
    """Flask-RESTful resource endpoint for a Braintree donation transaction."""

    def get( self ):
        """Endpoint to reprocess all queued donors in the redis queue."""

        response = reprocess_queued_donors()

        if response:
            return None, 200

        return None, 500

    def post( self ):
        """Endpoint to process given queued donor ID's in the redis queue."""

        response = reprocess_queued_donors( request.json )

        if response:
            return None, 200

        return None, 500
