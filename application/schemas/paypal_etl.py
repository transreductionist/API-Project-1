"""Marshmallow schema module for PaypalETLModel."""
# pylint: disable=too-few-public-methods
from marshmallow_sqlalchemy import ModelSchema

from application.flask_essentials import database
from application.models.paypal_etl import PaypalETLModel


class PaypalETLSchema( ModelSchema ):
    """Marshmallow schema for serialization/deserialization of PaypalETLModel."""

    class Meta:
        """Meta object for Marshmallow schema."""

        model = PaypalETLModel
        strict = True
        sqla_session = database.session
