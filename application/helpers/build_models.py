"""A module to support the construction of models given dictionaries across the application."""
from application.controllers.campaign import get_campaign_by_id
from application.controllers.campaign import get_campaigns_by_type
from application.exceptions.exception_critical_path import BuildModelsGiftTransactionsPathError
from application.exceptions.exception_critical_path import BuildModelsQueuedDonorPathError
from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from application.helpers.ultsys_user import create_user
from application.helpers.ultsys_user import find_ultsys_user
from application.helpers.ultsys_user import update_ultsys_user
from application.schemas.gift import GiftSchema
from application.schemas.queued_donor import QueuedDonorSchema
from application.schemas.transaction import TransactionSchema
# pylint: disable=bare-except
# flake8: noqa:E722


def build_models_sale( user, gift, transactions ):
    """Given the dictionaries for the models go ahead and build them.

    :param dict user: User dictionary with necessary model fields, and may have additional fields.
    :param dict gift: Gift dictionary with necessary model fields, and may have additional fields.
    :param transactions: The list of transactions. If this is a Braintree sale, for example, there will be one
           transaction in the list. On the other hand if this is an administrative sale where the method used is
           a check or money order there will be 2 transactions.
    :return:
    """

    # We are not caging at the front of the sale, and do that at the end.
    # The user is stored in QueuedDonorModel and the gift is given a user_id = -2
    user_id = -2

    # Build the gift model dictionary, and flush to get new auto-incremented gift_id.
    try:
        # Build the gift.
        if not gift[ 'campaign_id' ]:
            gift[ 'campaign_id' ] = None
        elif not get_campaign_by_id( gift[ 'campaign_id' ] ):
            gift[ 'campaign_id' ] = get_campaigns_by_type( 'is_default', 1 )[ 0 ].id

        gift[ 'user_id' ] = user_id
        gift_model = from_json( GiftSchema(), gift )
        database.session.add( gift_model.data )
        database.session.flush()
        gift_id = gift_model.data.id
        user[ 'gift_id' ] = gift_id
        user[ 'gift_searchable_id' ] = gift_model.data.searchable_id
        user[ 'campaign_id' ] = gift_model.data.campaign_id

        # Build the transactions.
        for transaction in transactions:
            transaction[ 'gift_id' ] = gift_id
            transaction_model = from_json( TransactionSchema(), transaction )
            database.session.add( transaction_model.data )
            database.session.flush()
            transaction[ 'id' ] = transaction_model.data.id
        database.session.commit()
    except:
        database.session.rollback()
        raise BuildModelsGiftTransactionsPathError()


def build_model_queued_donor( user ):
    """Given the dictionaries for the models go ahead and build them.

    :param dict queued_donor_user: User dictionary with necessary model fields, and may have additional fields.
    :return:
    """

    try:
        # Build queued donor here because: Gift needs user_id, and queued donor needs gift_id.
        queued_donor_model = from_json( QueuedDonorSchema(), user[ 'user_address' ] )
        queued_donor_model.data.gift_id = user[ 'gift_id' ]
        queued_donor_model.data.gift_searchable_id = user[ 'gift_searchable_id' ]
        queued_donor_model.data.campaign_id = user[ 'campaign_id' ]
        queued_donor_model.data.customer_id = user[ 'customer_id' ]
        database.session.add( queued_donor_model.data )
        database.session.flush()
        user[ 'queued_donor_id' ] = queued_donor_model.data.id
        database.session.commit()
    except:
        database.session.rollback()
        raise BuildModelsQueuedDonorPathError()


def build_model_new( user, gross_gift_amount ):
    """Given the new user save to model and return their ID.

    :param dict user: User dictionary with necessary model fields, and may have additional fields.
    :param gross_gift_amount: The gross gift amount.
    :return: The user ID
    """

    # Map the front-end keys to the user model keys.
    ultsys_user_json = {
        'firstname': user[ 'user_address' ][ 'user_first_name' ],
        'lastname': user[ 'user_address' ][ 'user_last_name' ],
        'zip': user[ 'user_address' ][ 'user_zipcode' ],
        'address': user[ 'user_address' ][ 'user_address' ],
        'city': user[ 'user_address' ][ 'user_city' ],
        'state': user[ 'user_address' ][ 'user_state' ],
        'email': user[ 'user_address' ][ 'user_email_address' ],
        'phone': user[ 'user_address' ][ 'user_phone_number' ],
        'donation_amount': gross_gift_amount
    }

    # If new user, there is no ID, create the DB entry and get it.
    drupal_uid = create_user( ultsys_user_json )

    query_parameters = {
        "action": "find",
        "search_terms": {
            "uid": { "eq": drupal_uid }
        },
        "sort_terms": []
    }

    ultsys_user = find_ultsys_user( query_parameters )

    user[ 'id' ] = ultsys_user[ 0 ][ 'ID' ]

    return user[ 'id' ]


def build_model_exists( user, gross_gift_amount ):
    """Given an existing user their ID that has been provided in the form or attached by caging.

    Update their latest donation information.

    :param dict user: User dictionary with necessary model fields, and may have additional fields.
    :param dict gross_gift_amount: The gross gift amount.
    """

    update_ultsys_user( user, gross_gift_amount )
