"""Resource entry point for the agent endpoints."""
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use
from nusa_jwt_auth.restful import AdminResource

from application.controllers.agent import get_agents
from application.schemas.agent import AgentSchema


class Agents( AdminResource ):
    """Flask-RESTful resource endpoints for AgentModel."""

    def get( self ):
        """Simple endpoint to retrieve all rows from table."""

        agents = get_agents()
        schema = AgentSchema( many=True )
        result = schema.dump( agents ).data
        return result, 200
