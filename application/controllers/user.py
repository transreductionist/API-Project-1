"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
from nusa_filter_param_parser.nusa_filter_param_parser import build_filter_from_request_args

from application.helpers.general_helper_functions import transform_to_ultsys_query
from application.helpers.ultsys_user import create_user
from application.helpers.ultsys_user import find_ultsys_user
from application.helpers.ultsys_user import update_ultsys_user


def ultsys_user( payload ):
    """Controller to handle request to the Ultsys user endpoint.

    There are 3 endpoints for the Ultsys user:

    create_user = {
        "action": "create",
        "id": null,
        "firstname: "Joe"
        "lastname: "Baker"
        "zip: "62918"
        "address: "1300 Crush Rd"
        "city: "BellaVerde"
        "state: "AK"
        "email: "jbaker@gmail.com"
        "phone: "6189853333"
    }

    update_ultsys_user = {
        "action": "update",
        "user": {
            "id": "321234"
        },
        "gift": {
            "gross_gift_amount": "100.00"
        }
    }

    The update endpoint will attach the current date to the payload on its way out.

    An example find_ultsys_user query string: donate/user?lastname=contains:Baker&sort=firstname:asc

    Gets deserialized into a dictionary, which then gets transformed to something like:

    find_ultsys_user = {
        "action": "find",
        "search_terms": {
            "lastname": { "like": "%Baker%" },
        },
        "sort_terms": [
            { "firstname": "ascending" }
        ]
    }

    :param dict payload: The JSON to pass on to the relevant function.
    :return: The requested data.
    """

    if 'action' in payload and payload[ 'action' ] == 'create':
        # This is the POST for creation of user through Drupal.
        request = create_user( payload )
    elif 'action' in payload and payload[ 'action' ] == 'update':
        # This is the PUT for the update of an Ultsys user.
        request = update_ultsys_user( payload[ 'user' ], payload[ 'gift' ] )
    else:
        # This is the GET a user from Ultsys with query string.

        # The payload is request.args and contains the query string within an ImmutableMultiDict.
        # The request.args is deserialized using filter_serialize_deserialize.py into query_dict.
        # The function filter_serialize_deserialize.py was built for NUSA applications and not Ultsys.
        # The document string in filter_serialize_deserialize.py has more detailed information.
        query_dict = build_filter_from_request_args( payload )
        query_parameters = transform_to_ultsys_query( query_dict )
        request = find_ultsys_user( query_parameters )

    return request
