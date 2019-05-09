"""The model for the test database UltsysUserModel used to test Ultsys endpoints more thoroughly.

Tables are explicitly named. The user table UltsysUserModel exists in the test database and not in the dev
database. It is used to provide data that can substitute for the Drupal/Ultsys data for users.
"""
# pylint: disable=too-few-public-methods
from application.flask_essentials import database


class UltsysUserModel( database.Model ):
    """A user model for testing.

    The Ultsys user model is part of the test database and allows the behavior of the Ultsys user endpoints to be
    mocked more thoroughly.
    """

    __tablename__ = 'user'
    ID = database.Column( database.Integer, primary_key=True, autoincrement=True, nullable=False )
    email = database.Column( database.VARCHAR( 255 ), nullable=False )
    firstname = database.Column( database.VARCHAR( 64 ), nullable=True, default='' )
    lastname = database.Column( database.VARCHAR( 64 ), nullable=True, default=None )
    address = database.Column( database.VARCHAR( 255 ), nullable=True, default=None )
    state = database.Column( database.VARCHAR( 2 ), nullable=True, default=None )
    city = database.Column( database.VARCHAR( 64 ), nullable=True, default=None )
    zip = database.Column( database.VARCHAR( 5 ), nullable=True, default=None )
    phone = database.Column( database.VARCHAR( 16 ), nullable=True, default=None )
    donation_prior_amount = database.Column( database.VARCHAR( 255 ), nullable=True, default=None )
    donation_sum = database.Column( database.VARCHAR( 255 ), nullable=True, default=None )
    donation_time = database.Column( database.DateTime, nullable=True )
    uid = database.Column( database.Integer, nullable=True )
