"""Marshmallow schema module for GiftThankYouLetterModel."""
# pylint: disable=too-few-public-methods
from marshmallow import fields
from marshmallow_sqlalchemy import ModelSchema

from application.flask_essentials import database
from application.models.gift_thank_you_letter import GiftThankYouLetterModel
from application.schemas.gift import GiftSchema


class GiftThankYouLetterSchema( ModelSchema ):
    """Marshmallow schema for serialization/deserialization of GiftThankYouLetterModel."""
    gift = fields.Nested( GiftSchema, dump_only=True )
    user = fields.Dict( dump_only=True )

    class Meta:
        """Meta object for Marshmallow schema."""

        model = GiftThankYouLetterModel
        strict = True
        sqla_session = database.session
