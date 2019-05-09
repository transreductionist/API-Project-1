"""The model for the Donations API service: agent table.

Tables are explicitly named. Care should be taken with the "type" fields as this is a common Python function.
Notice that the database=SQLAlchemy() is done through the import of flask_essentials. This will keep the Marshmallow
and model SQLAlchemy sessions the same. The Wiki has some information about this in the StackOverflow section.
"""
# pylint: disable=R0903
from application.flask_essentials import database


class AgentModel( database.Model ):
    """Agents model that defines who is modifying records."""

    __tablename__ = 'agent'
    id = database.Column(
        database.Integer, primary_key=True,
        autoincrement=True, nullable=False
    )
    name = database.Column( database.VARCHAR( 64 ), nullable=False, default='' )
    user_id = database.Column( database.Integer, nullable=True, default=None )
    staff_id = database.Column( database.Integer, nullable=True, default=None )
    type = database.Column(
        database.Enum( 'Staff Member', 'Organization', 'Automated', native_enum=False ),
        nullable=False, default='Staff Member'
    )

    @staticmethod
    def get_agent( agent_type, field, field_value ):
        """Place latest transaction status on the Gift."""
        equals_operator = '__eq__'
        column = getattr( AgentModel, field, None )
        filter_by_equals = getattr( column, equals_operator )( field_value )
        agent_model = AgentModel.query.filter( filter_by_equals ).one_or_none()
        if not agent_model:
            column = getattr( AgentModel, 'name', None )
            if agent_type == 'Staff Member':
                filter_by_equals = getattr( column, equals_operator )( 'Unknown Staff Member' )
            elif agent_type in ( 'Automated', 'Organization' ):
                filter_by_equals = getattr( column, equals_operator )( 'Unknown Organization' )
            agent_model = AgentModel.query.filter( filter_by_equals ).one_or_none()
        return agent_model
