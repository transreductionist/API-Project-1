"""Controllers for Flask-RESTful resources: provide endpoint to test health of application."""


def heartbeat():
    """Controller for simple heartbeat."""
    return True
