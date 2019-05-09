"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
from sqlalchemy.exc import SQLAlchemyError

from application.flask_essentials import database
from application.helpers.front_end_caging import ultsys_user_create
from application.helpers.front_end_caging import ultsys_user_update
from application.models.caged_donor import CagedDonorModel


def build_ultsys_user( payload ):
    """Controller to handle request to take a donor and create/update an Ultsys user.
    The payload from the front-end:

    payload = {
        "caged_donor_id": 102,
        "ultsys_user_id": 7042
    }

    :param dict payload: Data about the donor and how to cage.
    :return: The requested data.
    """

    if payload[ 'ultsys_user_id' ]:
        ultsys_user = ultsys_user_update( payload )
        return ultsys_user

    ultsys_user = ultsys_user_create( payload )
    return ultsys_user


def update_caged_donor( payload ):
    """Controller to handle updating a caged donor's address.
        payload = {
            "caged_donor_id": 102,
            "user_address": "328 Chauncey St",
            "user_city": "Bensonhurst",
            "user_state": "NY",
            "user_zipcode": "11214"
        }
    :param dict payload: Data about the donor to update.
    :return: The Boolean.
    """

    try:
        caged_donor_query = CagedDonorModel.query.filter_by( id=payload[ 'id' ] )
        caged_donor_query.update( payload )
    except SQLAlchemyError as error:
        database.session.rollback()
        raise error

    try:
        database.session.commit()
    except SQLAlchemyError as error:
        database.session.rollback()
        raise error

    return True
