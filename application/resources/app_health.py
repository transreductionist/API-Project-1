"""Resources entry point to test the health of the application."""
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use
from flask_api import status
from flask_restful import Resource

from application.controllers.app_health import heartbeat


class Heartbeat( Resource ):
    """Flask-RESTful resource endpoint to test the heartbeat of the application."""

    def get( self ):
        """Endpoint to to see if the application is running."""

        if heartbeat():
            return None, status.HTTP_200_OK

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR
