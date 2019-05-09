"""A helper module to define mocks for the Ultsys endpoints: find, create, and update."""
import json
from datetime import datetime
from decimal import Decimal

from flask_api import status

from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from application.helpers.model_serialization import to_json
from tests.helpers.ultsys_user_model import UltsysUserModel
from tests.helpers.ultsys_user_schema import UltsysUserSchema
# pylint: disable=too-few-public-methods


class Request:
    """Represents a mock of the request object with decode function."""

    def __init__( self, data ):
        self.content = self.Content( data )
        self.status_code = 200

    class Content:
        """The request content mock object with data and decode function."""

        def __init__( self, data ):
            self.data = data

        def decode( self, arg ):  # pylint: disable=unused-argument
            """The request object needs a mock of the decode function."""

            return json.dumps( self.data )


def get_ultsys_user( search_terms ):
    """The mocked function helpers.ultsys_user.get_ultsys_user.

    The function get_ultsys_user() makes a request.get() that returns user data based on search terms. The mocked
    function accepts only the search operator 'eq' and does not do chained searches. The argument to the function
    is a dictionary called search_terms:

    "search_terms": {
            "id": {"eq": "3239868"}
    }

    In the integration/unit tests the mocked functionsimple search for either last name, ID, or UID.

    :param search_terms:
    :return: A list of mocked ultsys user dictionaries matching the search criteria.
    """

    attribute = list( search_terms.copy().keys() )[ 0 ]
    attribute_value = search_terms[ attribute ][ 'eq' ]

    # The mock function doesn't have to handle the complete functionality of the endpoint.
    # Currently for sales it needs to handle lastname for caging, ID and UID for other cases.
    users_model_data = []
    if attribute == 'lastname':
        users_model_data = UltsysUserModel.query.filter_by( lastname=attribute_value ).all()
    elif attribute == 'ID':
        users_model_data = UltsysUserModel.query.filter_by( ID=attribute_value ).all()
    if attribute == 'uid':
        users_model_data = UltsysUserModel.query.filter_by( uid=attribute_value ).all()

    users_dict_data = []
    for user_model in users_model_data:
        user_dict = to_json( UltsysUserSchema(), user_model )
        users_dict_data.append( user_dict.data )

    request = Request( users_dict_data )
    return request


def update_ultsys_user( user, gross_gift_amount ):
    """The mocked function helpers.ultsys_user.update_ultsys_user.

    :param user: The user dictionary.
    :param gift: The gift dictionary.
    :return: HTTP status code
    """
    # This is what is sent to Drupal.
    user_parameters = {
        'id': user[ 'id' ],
        'donation_amount': gross_gift_amount,
        'donation_time': datetime.utcnow().strftime( '%Y-%m-%d %H:%M:%S' )
    }

    # This is what Drupal does to the Ultsys user.
    user_data = UltsysUserModel.query.filter_by( ID=user[ 'id' ] ).one_or_none()

    if user_data:
        user_data.donation_prior_amount = user_parameters[ 'donation_amount' ]

        donation_sum = Decimal( user_data.donation_sum ) + Decimal( user_data.donation_prior_amount )
        user_data.donation_sum = str( donation_sum )

        user_data.donation_time = user_parameters[ 'donation_time' ]

        return status.HTTP_200_OK

    return status.HTTP_404_NOT_FOUND


def create_user( user_parameters ):
    """A mock function to create a new user.

    :param dict user_parameters: The user dictionary to be created in the mocked ultsys user data.
    :return: The ID of the new user
    """

    user_model = from_json( UltsysUserSchema(), user_parameters, create=True )

    database.session.add( user_model.data )
    database.session.flush()

    # There are
    user_id = user_model.data.ID
    user_model.data.uid = user_id

    return user_id
