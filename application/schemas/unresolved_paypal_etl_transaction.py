"""Marshmallow schema module for UnresolvedPaypalETLTransactionModel."""
# pylint: disable=too-few-public-methods
from marshmallow_sqlalchemy import ModelSchema

from application.flask_essentials import database
from application.models.unresolved_paypal_etl_transaction import UnresolvedPaypalETLTransactionModel


class UnresolvedPaypalETLTransactionSchema( ModelSchema ):
    """Marshmallow schema for serialization/deserialization of UnresolvedPaypalETLTransactionModel."""

    class Meta:
        """Meta object for Marshmallow schema."""

        model = UnresolvedPaypalETLTransactionModel
        strict = True
        sqla_session = database.session
