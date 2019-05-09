"""A module for managing Ultsys users"""
from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from tests.helpers.mock_ultsys_user_data import ULTSYS_USER_DATA
from tests.helpers.ultsys_user_schema import UltsysUserSchema


def create_ultsys_users():
    """Create the ulytsys users.

    :return:
    """
    # Create some ultsys user data for the Ultsys endpoints wrapped in functions for mocking.
    user_models_data = []
    for user_dict in ULTSYS_USER_DATA:
        user_model = from_json( UltsysUserSchema(), user_dict, create=True )
        user_models_data.append( user_model.data )
    database.session.bulk_save_objects( user_models_data )
    database.session.commit()
