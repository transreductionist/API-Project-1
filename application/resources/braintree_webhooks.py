"""Resources entry point to handle Braintree webhooks."""
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use
from flask import request
from flask_api import status
from flask_restful import Resource

from application.controllers.braintree_webhooks import subscription_webhook


class BraintreeWebhookSubscription( Resource ):
    """Flask-RESTful resource endpoint for a Braintree subscription webhook."""

    def post( self ):
        """Endpoint to process posted data to the subscription webhook controller."""

        if subscription_webhook( request.form ):
            return None, status.HTTP_200_OK

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR
