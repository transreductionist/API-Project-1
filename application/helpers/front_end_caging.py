"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
from application.exceptions.exception_model import ModelCagedDonorNotFoundError
from application.exceptions.exception_model import ModelGiftNotFoundError
from application.exceptions.exception_model import ModelTransactionNotFoundError
from application.exceptions.exception_ultsys_user import UltsysUserNotFoundError
from application.flask_essentials import database
from application.helpers.model_serialization import to_json
from application.helpers.ultsys_user import create_user
from application.helpers.ultsys_user import find_ultsys_user
from application.helpers.ultsys_user import update_ultsys_user
from application.models.caged_donor import CagedDonorModel
from application.models.gift import GiftModel
from application.models.transaction import TransactionModel
from application.schemas.caged_donor import CagedDonorSchema


def ultsys_user_create( payload ):
    """Function to create an Ultsys user from a caged donor.

    payload = {
        "caged_donor_id": 1234,
        "ultsys_user_id": Null,
        "user_first_name": "Ralph",
        "user_last_name": "Kramden",
        "user_address": "328 Chauncey St",
        "user_state": "NY",
        "user_city": "Bensonhurst",
        "user_zipcode": "11214",
        "user_email_address": "ralph@gothambuscompany.com",
        "user_phone_number": "9172307441"
    }

    :param dict payload: The required payload
    :return: Ultsys user.
    """

    # Find the gift ID from the caged donor.
    caged_donor_model = CagedDonorModel.query.filter_by( id=payload[ 'caged_donor_id' ] ).one_or_none()
    if not caged_donor_model:
        raise ModelCagedDonorNotFoundError

    caged_donor_json = to_json( CagedDonorSchema(), caged_donor_model ).data
    caged_donor_json.pop( 'id' )

    # Retrieve the completed gift from the transactions to get the gross_gift_amount.
    gift = GiftModel.query.filter_by( id=caged_donor_model.gift_id ).one_or_none()
    if not gift:
        raise ModelGiftNotFoundError

    # The gift will have at least one transaction and may also have multiple transactions.
    # Get the most recent transaction which holds the current gross gift amount.
    transaction = TransactionModel.query.filter_by( gift_id=caged_donor_model.gift_id )\
        .order_by( TransactionModel.date_in_utc )\
        .first()
    if not transaction:
        raise ModelTransactionNotFoundError
    gross_gift_amount = transaction.gross_gift_amount

    # The updating of the caged donor fields does not expect the 2 IDs in the dictionary.

    # Build the payload for the Drupal user.
    caged_donor = {
        'action': 'create',
        'firstname': caged_donor_json[ 'user_first_name' ],
        'lastname': caged_donor_json[ 'user_last_name' ],
        'zip': caged_donor_json[ 'user_zipcode' ],
        'city': caged_donor_json[ 'user_city' ],
        'state': caged_donor_json[ 'user_state' ],
        'email': caged_donor_json[ 'user_email_address' ],
        'phone': str( caged_donor_json[ 'user_phone_number' ] )
    }

    drupal_user_uid = create_user( caged_donor )

    # Use the Drupal ID to retrieve the Ultsys user.
    ultsys_user = find_ultsys_user( get_ultsys_user_query( { 'drupal_user_uid': drupal_user_uid } ) )
    ultsys_user_id = ultsys_user[ 0 ][ 'ID' ]

    # Update the gift with the new Ultsys user ID and the Ultsys user with the gross gift amount.
    gift.user_id = ultsys_user_id
    update_ultsys_user( { 'id': ultsys_user_id }, gross_gift_amount )

    database.session.delete( caged_donor_model )
    database.session.commit()

    return ultsys_user[ 0 ]


def ultsys_user_update( payload ):
    """Function to update an Ultsys user through the Ultsys user service.
    :param dict payload: Ultsys user ID and caged donor ID.
    :return: Ultsys user.
    """

    # Validate Ultsys user.
    ultsys_user_id = payload[ 'ultsys_user_id' ]
    ultsys_user = find_ultsys_user( get_ultsys_user_query( { 'ultsys_user_id': ultsys_user_id } ) )
    if not ultsys_user:
        raise UltsysUserNotFoundError

    # Find the gift ID from the caged donor.
    caged_donor_model = CagedDonorModel.query.filter_by( id=payload[ 'caged_donor_id' ] ).one_or_none()
    if not caged_donor_model:
        raise ModelCagedDonorNotFoundError

    # From the gift ID retrieve the gift and then update its Ultsys user ID.
    gift = GiftModel.query.filter_by( id=caged_donor_model.gift_id ).one_or_none()
    if not gift:
        raise ModelGiftNotFoundError
    gift.user_id = ultsys_user_id

    # The gift will have at least one transaction and may also have multiple transactions.
    # Get the most recent transaction which holds the current gross gift amount.
    transaction = TransactionModel.query.filter_by( gift_id=caged_donor_model.gift_id )\
        .order_by( TransactionModel.date_in_utc )\
        .first()
    if not transaction:
        raise ModelTransactionNotFoundError
    gross_gift_amount = transaction.gross_gift_amount

    # Update the Ultsys user with the new donation and delete the caged donor.
    update_ultsys_user( { 'id': ultsys_user_id }, gross_gift_amount )
    database.session.delete( caged_donor_model )
    database.session.commit()
    updated_ultsys_user = find_ultsys_user( get_ultsys_user_query( { 'ultsys_user_id': ultsys_user_id } ) )

    return updated_ultsys_user[ 0 ]


def get_ultsys_user_query( user_id ):
    """To update the Ultsys user we need to find them.

    :param user_id: The Ultsys user ID
    :return: The user
    """

    query = {
        'action': 'find',
        'search_terms': {},
        'sort_terms': []
    }
    if 'ultsys_user_id' in user_id:
        query[ 'search_terms' ][ 'ID' ] = { 'eq': user_id[ 'ultsys_user_id' ] }
    elif 'drupal_user_uid' in user_id:
        query[ 'search_terms' ][ 'uid' ] = { 'eq': user_id[ 'drupal_user_uid' ] }
    return query


def update_payload( payload, donor_model ):
    """The function replaces any missing fields in the payload with the data for the caged donor in the database.

    :param payload: The payload from the front-end with user data.
    :param donor_model: The donor_model for the caged donor of the data.
    :return:
    """

    for donor_key, donor_value in payload.items():
        if isinstance( donor_value, str ) and donor_value.strip() == '':
            donor_value = None
        if not donor_value:
            payload[ donor_key ] = getattr( donor_model, donor_key )
