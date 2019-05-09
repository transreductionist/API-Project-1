"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
from application.models.agent import AgentModel


def get_agents():
    """Simple query to return all agents."""

    agents = AgentModel.query.all()
    return agents
