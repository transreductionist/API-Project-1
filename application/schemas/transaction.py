"""Marshmallow schema module for TransactionModel."""
# pylint: disable=too-few-public-methods
from marshmallow import fields
from marshmallow import post_dump
from marshmallow_sqlalchemy import ModelSchema

from application.flask_essentials import database
from application.models.transaction import TransactionModel


class TransactionSchema( ModelSchema ):
    """Marshmallow schema for serialization/deserialization of TransactionModel."""

    # Need to handle Decimal fields correctly on serialization/deserialization.
    gross_gift_amount = fields.Decimal( places=2, as_string=True, required=True )
    fee = fields.Decimal( places=2, as_string=True, required=False )
    date_in_utc = fields.DateTime()
    gift_searchable_id = fields.Str( dump_only=True )

    class Meta:
        """Meta object for Marshmallow schema."""
        exclude = [ 'gift' ]
        model = TransactionModel
        strict = True
        sqla_session = database.session

    @post_dump
    def strip_gift_id( self, transaction ):  # pylint: disable=no-self-use
        """Need to strip the gift ID from a transaction for various endpoints.

        :param transaction:
        :return:
        """

        if 'gift_id' in transaction:
            del transaction[ 'gift_id' ]
