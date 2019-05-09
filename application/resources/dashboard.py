"""Resource entry point for getting dashboard data."""
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use
from nusa_jwt_auth.restful import AdminResource

from application.controllers.dashboard import get_dashboard_data


class DashboardData( AdminResource ):
    """Flask-RESTful resource endpoints for data."""

    def get( self, data_type ):
        """Simple endpoint to retrieve summary data."""

        return get_dashboard_data( data_type ), 200
