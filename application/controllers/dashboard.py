"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
from application.helpers.dashboard import dashboard_data


def get_dashboard_data( data_type ):
    """An endpoint that returns donors filtered by the query terms, paginated, and sorted."""

    data_json = dashboard_data( data_type )
    return data_json
