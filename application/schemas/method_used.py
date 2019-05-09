"""Marshmallow schema module for MethodUsedModel."""
# pylint: disable=too-few-public-methods
from marshmallow_sqlalchemy import ModelSchema

from application.flask_essentials import database
from application.models.method_used import MethodUsedModel


class MethodUsedSchema( ModelSchema ):
    """Marshmallow schema for serialization/deserialization of MethodUsedModel."""

    class Meta:
        """Meta object for Marshmallow schema."""

        model = MethodUsedModel
        strict = True
        sqla_session = database.session
