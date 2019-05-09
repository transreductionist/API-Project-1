"""Marshmallow schema module for CagedDonorModel."""
# pylint: disable=too-few-public-methods
from marshmallow import fields
from marshmallow_sqlalchemy import ModelSchema

from application.flask_essentials import database
from application.models.caged_donor import CagedDonorModel


class CagedDonorSchema( ModelSchema ):
    """Marshmallow schema for serialization/deserialization of CagedDonorModel."""

    gift_searchable_id = fields.UUID()

    class Meta:
        """Meta object for Marshmallow schema."""

        exclude = [ 'gift_id' ]
        model = CagedDonorModel
        strict = True
        sqla_session = database.session
