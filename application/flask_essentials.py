"""Create instantiations of SQLAlchemy and Marshmallow(): Helps to synchronize sessions."""
from flask_marshmallow import Marshmallow
from flask_rq2 import RQ
from flask_sqlalchemy import SQLAlchemy
from nusa_jwt_auth import NUSAJwtManager

database = SQLAlchemy()  # pylint: disable=invalid-name
marshmallow = Marshmallow()  # pylint: disable=invalid-name
redis_queue = RQ()  # pylint: disable=invalid-name
jwt = NUSAJwtManager()  # pylint: disable=invalid-name
