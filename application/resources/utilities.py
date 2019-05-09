"""The Resources entry point for utility endpoints"""
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use
from nusa_jwt_auth.restful import AdminResource

from application.controllers.utilities import get_enumeration


class Enumeration( AdminResource ):
    """Flask-RESTful resource endpoints to get an enumeration on a model."""

    def get( self, model, attribute ):
        """Retrieve the enumeration values from the specified model and attribute.

        :param model: The model to retrieve the enumeration from.
        :param attribute: The enumeration attribute on the model.
        :return: List of the enumeration values.
        """

        enumeration_list = get_enumeration( model, attribute )
        return enumeration_list, 200
