"""The model for the Donations API service: queued_donor table.

When a donation is made the donor is queued in the queued_donor table. The gift is assigned to the donor and they are
caged as a queued job. It can take up to 30 seconds to cage this donor. Once they are caged the gift and users are
updated.

Tables are explicitly named. Notice that the database=SQLAlchemy() is done through the import of flask_essentials. This
will keep the Marshmallow and model SQLAlchemy sessions the same. The Wiki has some information about this in the
StackOverflow section.
"""
# pylint: disable=R0903
from application.flask_essentials import database
from application.models.binary_uuid import BinaryUUID


class QueuedDonorModel( database.Model ):
    """If a donor cannot be confidently associated with an existing user cage them."""

    __tablename__ = 'queued_donor'
    id = database.Column( database.Integer, primary_key=True, autoincrement=True, nullable=False )
    gift_id = database.Column( database.Integer, nullable=True )
    gift_searchable_id = database.Column( BinaryUUID, nullable=True )
    campaign_id = database.Column( database.Integer, nullable=True, default=None )
    customer_id = database.Column( database.VARCHAR( 36 ), nullable=True, default='' )
    user_email_address = database.Column( database.VARCHAR( 255 ), nullable=False, default=None )
    user_first_name = database.Column( database.VARCHAR( 64 ), nullable=True, default='' )
    user_last_name = database.Column( database.VARCHAR( 64 ), nullable=True, default=None )
    user_address = database.Column( database.VARCHAR( 255 ), nullable=True, default=None )
    user_state = database.Column( database.CHAR( 2 ), nullable=True, default=None )
    user_city = database.Column( database.VARCHAR( 64 ), nullable=True, default=None )
    user_zipcode = database.Column( database.VARCHAR( 5 ), nullable=True, default=None )
    user_phone_number = database.Column( database.BigInteger, nullable=True, default=0 )
    times_viewed = database.Column( database.Integer, nullable=True )
