"""Marshmallow schema module for the test database UltsysUserModel."""
# pylint: disable=too-few-public-methods
from marshmallow_sqlalchemy import ModelSchema

from application.flask_essentials import database
from tests.helpers.ultsys_user_model import UltsysUserModel


class UltsysUserSchema( ModelSchema ):
    """Marshmallow schema for serialization/deserialization of the stand-in UserModel."""

    class Meta:
        """Meta object for User Marshmallow schema."""

        model = UltsysUserModel
        strict = True
        sqla_session = database.session
