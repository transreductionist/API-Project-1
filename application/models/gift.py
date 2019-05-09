"""The model for the Donations API service: gift table.

Tables are explicitly named. Notice that the database=SQLAlchemy() is done through the import of flask_essentials.
This will keep the Marshmallow and model SQLAlchemy sessions the same. The Wiki has some information about this in the
StackOverflow section.
"""
# pylint: disable=R0903
import uuid

from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.ext.hybrid import hybrid_property

from application.flask_essentials import database
from application.models.binary_uuid import BinaryUUID
from application.models.transaction import TransactionModel


class GiftModel( database.Model ):
    """Head, or master table, for donations."""

    __tablename__ = 'gift'
    id = database.Column( database.Integer, primary_key=True, autoincrement=True, nullable=False )
    searchable_id = database.Column( BinaryUUID, nullable=False, default=uuid.uuid4 )
    user_id = database.Column( database.Integer, nullable=True, default=None )
    campaign_id = database.Column( database.Integer, nullable=True, default=None )
    customer_id = database.Column( database.VARCHAR( 36 ), nullable=True, default='' )
    method_used_id = database.Column( TINYINT, nullable=False, default=1 )
    sourced_from_agent_id = database.Column( database.Integer, nullable=True, default=None )
    given_to = database.Column(
        database.Enum( 'ABI', 'ACTION', 'BECK', 'GREEN', 'INTER', 'MCRI', 'NERF', 'P-USA', 'PROD', 'UNRES', 'VIDEO',
                       'TBD', 'SUPPORT', native_enum=False ), default='ACTION', nullable=False
    )
    recurring_subscription_id = database.Column( database.VARCHAR( 32 ), nullable=True, default=None )
    transactions = database.relationship(
        'TransactionModel',
        order_by='desc( TransactionModel.date_in_utc )',
        foreign_keys=[ TransactionModel.gift_id ],
        primaryjoin='GiftModel.id == TransactionModel.gift_id'
    )

    @hybrid_property
    def date_in_utc( self ):
        """Place latest transaction date_in_utc on the Gift."""
        if self.transactions:
            return self.transactions[ 0 ].date_in_utc
        return None

    @hybrid_property
    def status( self ):
        """Place latest transaction status on the Gift."""
        if self.transactions:
            return self.transactions[ 0 ].status
        return None

    @hybrid_property
    def gross_gift_amount( self ):
        """Place latest transaction gross_gift_amount on the Gift."""
        if self.transactions:
            return self.transactions[ 0 ].gross_gift_amount
        return None
