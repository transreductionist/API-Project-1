"""The model for the Donations API service: donation_types table.

Tables are explicitly named. Notice that the database=SQLAlchemy() is done through the import of flask_essentials.
This will keep the Marshmallow and model SQLAlchemy sessions the same. The Wiki has some information about this in
the StackOverflow section.
"""
# pylint: disable=R0903
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.dialects.mysql import TINYINT

from application.flask_essentials import database


class MethodUsedModel( database.Model ):
    """Agents model that defines who is modifying records."""

    __tablename__ = 'method_used'
    id = database.Column( BIGINT, primary_key=True, autoincrement=True, nullable=False )
    name = database.Column( database.VARCHAR( 128 ), nullable=False, default='Web Form Credit Card' )
    billing_address_required = database.Column( TINYINT, nullable=False, default=0 )

    @staticmethod
    def get_method_used( field, field_value ):
        """Place latest transaction status on the Gift."""
        equals_operator = '__eq__'
        column = getattr( MethodUsedModel, field, None )
        filter_by_equals = getattr( column, equals_operator )( field_value )
        method_used_model = MethodUsedModel.query.filter( filter_by_equals ).one_or_none()
        if not method_used_model:
            column = getattr( MethodUsedModel, 'name', None )
            filter_by_equals = getattr( column, equals_operator )( 'Unknown Method Used' )
            method_used_model = MethodUsedModel.query.filter( filter_by_equals ).one_or_none()
        return method_used_model
