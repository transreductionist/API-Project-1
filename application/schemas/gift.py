"""Schema for GiftModel: incorporates data from relationship() join to TransactionModel."""
# pylint: disable=too-few-public-methods
from marshmallow import fields
from marshmallow_sqlalchemy import ModelSchema

from application.flask_essentials import database
from application.models.gift import GiftModel
from application.schemas.transaction import TransactionSchema

TRANSACTION_ATTRIBUTES = ( 'transactions', 'gross_gift_amount', 'date_in_utc', 'status' )
GIFT_ATTRIBUTES = ( 'id', 'user_id', 'method_used_id', 'sourced_by_agent_id', 'given_to', 'recurring_subscription_id' )


class GiftSchema( ModelSchema ):
    """Marshmallow schema for serialization/deserialization of GiftModel."""

    searchable_id = fields.UUID()

    transactions = fields.List(
        fields.Nested(
            TransactionSchema,
            only=[
                'id', 'date_in_utc', 'enacted_by_agent_id', 'type', 'status',
                'reference_number', 'gross_gift_amount', 'fee', 'notes'
            ]
        )
    )
    date_in_utc = fields.DateTime()
    gross_gift_amount = fields.Decimal( places=2, as_string=True, required=True )
    status = fields.String()
    receipt_sent = fields.DateTime()

    class Meta:
        """Meta object for Marshmallow schema."""

        exclude = [ 'id' ]
        dump_only = TRANSACTION_ATTRIBUTES
        model = GiftModel
        strict = True
        sqla_session = database.session
