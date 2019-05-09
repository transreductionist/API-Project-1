"""The model for the Donations API service: Campaign and CampaignAmounts tables.

Tables are explicitly named. Care should be taken with the "type" fields as this is a common Python function. Notice
that the database=SQLAlchemy() is done through the import of flask_essentials. This will keep the Marshmallow and model
SQLAlchemy sessions the same. The Wiki has some information about this in the StackOverflow section.
"""
# pylint: disable=R0903
from application.flask_essentials import database


class CampaignModel( database.Model ):
    """A campaign model to persist ."""

    __tablename__ = 'campaign'
    id = database.Column( database.Integer, primary_key=True, autoincrement=True, nullable=False )
    name = database.Column( database.VARCHAR( 80 ), nullable=True )
    description = database.Column( database.VARCHAR( 80 ), nullable=True )
    date_from_utc = database.Column( database.DateTime, nullable=True )
    date_to_utc = database.Column( database.DateTime, nullable=True )
    message = database.Column( database.TEXT(), nullable=True )
    photo_type = database.Column( database.VARCHAR( 80 ), nullable=True )
    background = database.Column( database.Integer, nullable=True )
    video_name = database.Column( database.VARCHAR( 80 ), nullable=True )
    video_url = database.Column( database.VARCHAR( 80 ), nullable=True )
    is_active = database.Column( database.Integer, nullable=True, default=1 )
    is_default = database.Column( database.Integer, nullable=True, default=0 )


class CampaignAmountsModel( database.Model ):
    """A user model that associates an amount ID with a campaign ID."""

    __tablename__ = 'campaign_amounts'
    id = database.Column( database.Integer, primary_key=True, autoincrement=True, nullable=False )
    amount = database.Column( database.DECIMAL( 10, 2 ), nullable=False )
    weight = database.Column( database.Integer, nullable=True )
    campaign_id = database.Column( database.Integer, nullable=True, default=None )
