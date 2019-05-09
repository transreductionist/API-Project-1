"""The model for the Donations API service: transaction table.

Tables are explicitly named. Care should be taken with the "type" fields as this is a common Python function. Notice
that the database=SQLAlchemy() is done through the import of flask_essentials. This will keep the Marshmallow and model
SQLAlchemy sessions the same. The Wiki has some information about this in the StackOverflow section.
"""
# pylint: disable=R0903
from sqlalchemy.ext.hybrid import hybrid_property

from application.flask_essentials import database


class TransactionModel( database.Model ):
    """A general transaction model to include Braintree and other donations."""

    __tablename__ = 'transaction'
    id = database.Column( database.Integer, primary_key=True, autoincrement=True, nullable=False )
    gift_id = database.Column( database.Integer, nullable=False )
    date_in_utc = database.Column( database.DateTime, nullable=False )
    receipt_sent_in_utc = database.Column( database.DateTime, nullable=True )
    enacted_by_agent_id = database.Column( database.Integer, nullable=True, default=None )
    type = database.Column(
        database.Enum(
            'Gift', 'Correction', 'Refund', 'Deposit to Bank', 'Bounced', 'Void', 'Dispute', 'Note',
            'Fine',
            native_enum=False
        ),
        default='Gift',
        nullable=False
    )
    status = database.Column(
        database.Enum(
            'Accepted', 'Completed', 'Declined', 'Denied', 'Failed', 'Forced', 'Lost', 'Refused', 'Requested',
            'Won', 'Thank You Sent', native_enum=False
        ),
        default='Accepted',
        nullable=True
    )
    reference_number = database.Column( database.VARCHAR( 32 ), nullable=True, default='' )
    gross_gift_amount = database.Column( database.DECIMAL( 10, 2 ), nullable=False )
    fee = database.Column( database.DECIMAL( 8, 2 ), nullable=False )
    notes = database.Column( database.Text, nullable=True )
    gift = database.relationship(
        'GiftModel',
        foreign_keys=[ gift_id ],
        primaryjoin='TransactionModel.gift_id == GiftModel.id',
        uselist=False
    )

    @hybrid_property
    def gift_searchable_id( self ):
        """Add gift_searchable_id property to Transaction object"""

        if self.gift:
            return self.gift.searchable_id
        return None
