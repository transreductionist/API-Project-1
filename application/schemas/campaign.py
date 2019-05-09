"""Marshmallow schema module for CampaignModel."""
# pylint: disable=too-few-public-methods
from marshmallow import fields
from marshmallow_sqlalchemy import ModelSchema

from application.flask_essentials import database
from application.models.campaign import CampaignAmountsModel
from application.models.campaign import CampaignModel


class CampaignSchema( ModelSchema ):
    """Marshmallow schema for serialization/deserialization of CampaignModel."""
    date_from_utc = fields.DateTime()
    date_to_utc = fields.DateTime()

    class Meta:
        """Meta object for Marshmallow schema."""

        model = CampaignModel
        strict = True
        sqla_session = database.session


class CampaignAmountsSchema( ModelSchema ):
    """Marshmallow schema for serialization/deserialization of CampaignAmountsModel."""
    amount = fields.Decimal( places=2, as_string=True, required=True )

    class Meta:
        """Meta object for Marshmallow schema."""

        model = CampaignAmountsModel
        strict = True
        sqla_session = database.session
