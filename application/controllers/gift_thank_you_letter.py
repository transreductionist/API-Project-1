"""Controllers for Flask-RESTful resources: handle the business logic for the Thank you letter endpoint."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from flask import current_app
from s3_web_storage.web_storage import WebStorage
from sqlalchemy.exc import SQLAlchemyError

from application.exceptions.exception_ultsys_user import UltsysUserMultipleFoundError
from application.exceptions.exception_ultsys_user import UltsysUserNotFoundError
from application.flask_essentials import database
from application.helpers.build_output_file import build_flat_bytesio_csv
from application.helpers.general_helper_functions import get_date_with_day_suffix
from application.helpers.model_serialization import to_json
from application.helpers.ultsys_user import find_ultsys_user
from application.models.caged_donor import CagedDonorModel
from application.models.gift import GiftModel
from application.models.gift_thank_you_letter import GiftThankYouLetterModel
from application.models.queued_donor import QueuedDonorModel
from application.models.transaction import TransactionModel
from application.schemas.transaction import TransactionSchema
# pylint: disable=bare-except


def get_not_yet_thank_you_gifts():
    """Endpoint to get all gift IDs without a thank you letter.

    :return: all rows in gift_thank_you_letter table
    """

    gifts = GiftThankYouLetterModel.query.all()
    gifts = [ gift for gift in gifts if gift.user ]

    return gifts


def handle_thank_you_letter_logic( searchable_ids, enacted_by_agent_id ):
    """The code to handle the model for a thank you letter being sent.

    We have from the front-end the following searchable_ids:

    searchable_ids = [ searchable_id_1, searchable_id_2, ... ] or possible and empty list ( [] 0.

    When thank you letters are sent:
      1. Get the agent ID using the Ultsys ID from the JWT in the resource.
      2. Build out gift ID's and user for thank you letters.
      3. Create new transactions with type: Thank You Sent

      Return to resource where thank you is emailed.

    :param searchable_ids: The gift searchable IDs to build thank yous for.
    :param enacted_by_agent_id: The agent processing the batch of thank yous.
    :return: The thank you dictionaries and the URL to the CSV.
    """

    thank_you_dicts = []
    transaction_models = []

    if not searchable_ids:
        searchable_ids_tmp = database.session.query( GiftModel.searchable_id )\
            .join( GiftThankYouLetterModel, GiftModel.id == GiftThankYouLetterModel.gift_id ).all()
        searchable_ids = [ str( searchable_id[ 0 ].hex.upper() ) for searchable_id in searchable_ids_tmp ]

    # 2. New transaction with Thank You Sent type
    gift_searchable_ids, gift_ids = build_out_gift_ids( searchable_ids )
    user_data = build_out_user_data( searchable_ids )

    for searchable_id in searchable_ids:
        thank_you_dict = {}
        transaction_model = TransactionModel(
            gift_id=gift_searchable_ids[ searchable_id ][ 'gift_id' ],
            date_in_utc=datetime.utcnow(),
            enacted_by_agent_id=enacted_by_agent_id,
            type=gift_searchable_ids[ searchable_id ][ 'type' ],
            status='Thank You Sent',
            reference_number=gift_searchable_ids[ searchable_id ][ 'reference_number' ],
            gross_gift_amount=gift_searchable_ids[ searchable_id ][ 'gross_gift_amount' ],
            fee=Decimal( 0.00 ),
            notes='Thank you email sent.'
        )
        transaction_models.append( transaction_model )
        thank_you_dict[ 'transaction' ] = to_json( TransactionSchema(), transaction_model ).data
        thank_you_dict[ 'transaction' ][ 'gift_id' ] = gift_searchable_ids[ searchable_id ][ 'gift_id' ]

        thank_you_dict[ 'gift' ] = gift_searchable_ids[ searchable_id ]
        thank_you_dict[ 'user' ] = user_data[ searchable_id ]
        thank_you_dicts.append( thank_you_dict )
    try:
        GiftThankYouLetterModel.query\
            .filter( GiftThankYouLetterModel.gift_id.in_( gift_ids ) )\
            .delete( synchronize_session='fetch' )
        database.session.add_all( transaction_models )
        database.session.flush()
    except SQLAlchemyError as error:
        database.session.rollback()
        raise error

    try:
        database.session.commit()
    except SQLAlchemyError as error:
        database.session.rollback()
        raise error

    # 3. Create a CSV of the results.
    url = build_thank_you_letters_csv( thank_you_dicts )

    return thank_you_dicts, url


def build_out_gift_ids( searchable_ids ):
    """Build a lookup table from searchable to gift ID, as well as construct a list of Gift IDs to delete.

    :param searchable_ids: Gift searchable IDs.
    :return: A dictionary of gift information on the gift searchable IDs provided.
    """

    searchable_ids_uuid = [ UUID( searchable_id ) for searchable_id in searchable_ids ]
    gift_searchable_ids = {}
    gift_ids = []
    for searchable_id_uuid in searchable_ids_uuid:
        gift = GiftModel.query.filter_by( searchable_id=searchable_id_uuid ).one_or_none()
        if gift:
            gift_transactions = TransactionModel.query.filter_by( gift_id=gift.id ).all()

            first_transaction = gift_transactions[ 0 ]
            latest_transaction = gift_transactions[ len( gift_transactions ) - 1 ]

            gift_searchable_ids[ searchable_id_uuid.hex.upper() ] = {
                'gift_id': gift.id,
                'given_to': gift.given_to,
                'user_id': gift.user_id,
                'date_in_utc': get_date_with_day_suffix( first_transaction.date_in_utc ),
                'type': latest_transaction.type,
                'reference_number': latest_transaction.reference_number,
                'gross_gift_amount': latest_transaction.gross_gift_amount,
                'transaction_id': first_transaction.id
            }
            gift_ids.append( gift.id )
    return gift_searchable_ids, gift_ids


def build_out_user_data( searchable_ids ):
    """Build a lookup table from searchable to gift ID, as well as construct a list of Gift IDs to delete.

    :param searchable_ids: The searchable IDs to process.
    :return: User data based upon the user ID on the gift.
    """

    searchable_ids_uuid = [ UUID( searchable_id ) for searchable_id in searchable_ids ]
    user_data = {}
    for searchable_id_uuid in searchable_ids_uuid:
        gift = GiftModel.query.filter_by( searchable_id=searchable_id_uuid ).one_or_none()
        if gift:
            user_id = gift.user_id

            donor_model = { -1: CagedDonorModel, -2: QueuedDonorModel }
            if user_id in [ -1, -2 ]:
                donor = donor_model[ user_id ].query.filter_by( gift_id=gift.id ).one_or_none()
                user = [ {
                    'firstname': donor.user_first_name,
                    'lastname': donor.user_last_name,
                    'honorific': '',
                    'suffix': '',
                    'address': donor.user_address,
                    'city': donor.user_city,
                    'state': donor.user_state,
                    'zip': donor.user_zipcode,
                    'email': donor.user_email_address
                } ]
            else:
                user_query_terms = { 'action': 'find', 'search_terms': { 'ID': { 'eq': user_id } }, 'sort_terms': [ ] }
                user = find_ultsys_user( user_query_terms )

            # Ensure the number of users returned is correct: 1.
            # Need to definitely catch no users found, and might as well protect against multiple users found.
            if not user:
                raise UltsysUserNotFoundError
            if len( user ) >= 2:
                raise UltsysUserMultipleFoundError

            user_data[ searchable_id_uuid.hex.upper() ] = {
                'user_address': {
                    'user_short_first_name': user[ 0 ][ 'firstname' ],
                    'user_honorific': user[ 0 ][ 'honorific' ],
                    'user_first_name': user[ 0 ][ 'firstname' ],
                    'user_last_name': user[ 0 ][ 'lastname' ],
                    'user_suffix': user[ 0 ][ 'suffix' ],
                    'user_address': user[ 0 ][ 'address' ],
                    'user_city': user[ 0 ][ 'city' ],
                    'user_state': user[ 0 ][ 'state' ],
                    'user_zipcode': user[ 0 ][ 'zip' ].zfill( 5 ),
                    'user_email_address': user[ 0 ][ 'email' ]
                },
                'billing_address': {}
            }

    return user_data


def build_thank_you_letters_csv( thank_you_dicts ):
    """Build the thank you letter CSVs.

    :param thank_you_dicts: A dictionary containing transaction, gift and user data.
    :return: A URL to the CSV file on AWS S3.
    """

    header = [
        'DateOfGift', 'Amount', 'Account', 'UserID', 'TransactionID', 'CheckNumber', 'Shortfirstname', 'Honorific',
        'Firstname', 'Lastname', 'Suffix', 'Address', 'City', 'State', 'Zip'
    ]
    WebStorage.init_storage(
        current_app, current_app.config[ 'AWS_CSV_FILES_BUCKET' ],
        current_app.config[ 'AWS_CSV_FILES_PATH' ]
    )

    results = []
    for thank_you_dict in thank_you_dicts:

        result = [
            thank_you_dict[ 'gift' ][ 'date_in_utc' ],
            thank_you_dict[ 'transaction' ][ 'gross_gift_amount' ],
            thank_you_dict[ 'gift' ][ 'given_to' ],
            thank_you_dict[ 'gift' ][ 'user_id' ],
            thank_you_dict[ 'gift' ][ 'transaction_id' ],
            thank_you_dict[ 'transaction' ][ 'reference_number' ],
            thank_you_dict[ 'user' ][ 'user_address' ][ 'user_short_first_name' ],
            thank_you_dict[ 'user' ][ 'user_address' ][ 'user_honorific' ],
            thank_you_dict[ 'user' ][ 'user_address' ][ 'user_first_name' ],
            thank_you_dict[ 'user' ][ 'user_address' ][ 'user_suffix' ],
            thank_you_dict[ 'user' ][ 'user_address' ][ 'user_address' ],
            thank_you_dict[ 'user' ][ 'user_address' ][ 'user_city' ],
            thank_you_dict[ 'user' ][ 'user_address' ][ 'user_state' ],
            thank_you_dict[ 'user' ][ 'user_address' ][ 'user_zipcode' ]
        ]
        results.append( result )

    url = None
    if results:
        file_name = build_flat_bytesio_csv( results, header, 'thank_you_letters', True )

        url = WebStorage.generate_presigned_url(
            current_app.config[ 'AWS_CSV_FILES_BUCKET' ],
            current_app.config[ 'AWS_CSV_FILES_PATH' ] + file_name
        )

    return url
