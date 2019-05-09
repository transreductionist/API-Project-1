"""Marshmallow schema module for QueuedDonorModel."""
# pylint: disable=too-few-public-methods
from marshmallow import fields
from marshmallow_sqlalchemy import ModelSchema

from application.flask_essentials import database
from application.models.queued_donor import QueuedDonorModel


class QueuedDonorSchema( ModelSchema ):
    """Marshmallow schema for serialization/deserialization of QueuedDonorModel."""

    gift_searchable_id = fields.UUID()

    class Meta:
        """Meta object for Marshmallow schema."""

        exclude = [ 'gift_id' ]
        model = QueuedDonorModel
        strict = True
        sqla_session = database.session
