"""The model for the Donations API service: paypal_etl table."""
# pylint: disable=R0903
from application.flask_essentials import database


class PaypalETLModel( database.Model ):
    """PaypalETLs model"""

    __tablename__ = 'paypal_etl'
    id = database.Column(
        database.Integer, primary_key=True,
        autoincrement=True, nullable=False
    )
    enacted_by_agent_id = database.Column( database.Integer, nullable=False )
    file_name = database.Column( database.VARCHAR( 128 ), nullable=False )
    date_in_utc = database.Column( database.DateTime, nullable=False )
