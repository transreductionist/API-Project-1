"""Marshmallow schema module for AgentModel."""
# pylint: disable=too-few-public-methods
from marshmallow_sqlalchemy import ModelSchema

from application.flask_essentials import database
from application.models.agent import AgentModel


class AgentSchema( ModelSchema ):
    """Marshmallow schema for serialization/deserialization of AgentModel."""

    class Meta:
        """Meta object for Marshmallow schema."""

        model = AgentModel
        strict = True
        sqla_session = database.session
