"""The model for the Donations API service: unresolved_paypal_etl_transaction table."""
# pylint: disable=R0903
from application.flask_essentials import database


class UnresolvedPaypalETLTransactionModel( database.Model ):
    """In the PayPal CSV upload there are a class of transactions that cannot be resolved."""

    __tablename__ = 'unresolved_paypal_etl_transaction'
    id = database.Column( database.Integer, primary_key=True, autoincrement=True, nullable=False )
    enacted_by_agent_id = database.Column( database.Integer, nullable=True )
    date = database.Column( database.VARCHAR( 20 ), nullable=True, default=None )
    time = database.Column( database.VARCHAR( 20 ), nullable=True, default=None )
    time_zone = database.Column( database.VARCHAR( 5 ), nullable=True, default=None )
    name = database.Column( database.VARCHAR( 255 ), nullable=True, default=None )
    type = database.Column( database.VARCHAR( 255 ), nullable=True, default=None )
    status = database.Column( database.VARCHAR( 64 ), nullable=True, default=None )
    subject = database.Column( database.VARCHAR( 255 ), nullable=True, default=None )
    gross = database.Column( database.VARCHAR( 64 ), nullable=True, default=None )
    fee = database.Column( database.VARCHAR( 64 ), nullable=True, default=None )
    from_email_address = database.Column( database.VARCHAR( 255 ), nullable=True, default=None )
    to_email_address = database.Column( database.VARCHAR( 255 ), nullable=True, default=None )
    transaction_id = database.Column( database.VARCHAR( 255 ), nullable=True, default=None )
    reference_txn_id = database.Column( database.VARCHAR( 255 ), nullable=True, default=None )
