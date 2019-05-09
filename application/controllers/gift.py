"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
from datetime import datetime
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from application.flask_essentials import database
from application.helpers.gift_helpers import build_gifts_from_query
from application.helpers.model_serialization import from_json
from application.helpers.sql_queries import query_gift_equal_uuid
from application.helpers.sql_queries import query_gift_like_uuid
from application.models.agent import AgentModel
from application.models.gift import GiftModel
from application.models.transaction import TransactionModel
from application.schemas.transaction import TransactionSchema

DATE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def get_gifts( query_terms, page_information=None, sort_information=None ):
    """An endpoint that returns gifts filtered by the query terms, paginated, and sorted.

    The resource separates the query, paginate, and sort terms returned by the request.args parser separately.
    If there are no query terms all gifts are returned, otherwise the filtered gifts are returned. Pagination and
    sorting are handled if requested.

    Here is an example of query, paginate and sort terms as they might appear in the URL: &given_to=NERF&user_id=4
        &gross_gift_amount=20&type=Gift&status=Accepted&sort=id:desc&rows_per_page=25&page_number=3

    Notice that the endpoint accepts both GiftModel and TransactionModel fields without a prefix such as
    gift.method_used. The GiftModel and TransactionModel fields are disjoint.

    :param list query_terms: A dictionary of query terms.
    :param dict page_information: Paginate terms.
    :param dict sort_information: Sort terms.
    :return: A list of gifts.
    """

    gifts = build_gifts_from_query( query_terms, page_information, sort_information )
    return gifts


def get_gifts_by_date( date ):
    """Query to return gifts based on dates of attached Transactions.

    If a list of dates is provided, Transactions are searched for the given date range, and then the associated gifts
    are returned. If one date is provided as a parameter, Transactions are searched which were created on or after
    that date, and all their associated gifts returned. The function does some payload validation, and ensures that
    if two dates are provided they are also sequential.

    The post payload looks like: { "date": "2018-02-12" } or { "date": [ "2018-02-01", "2018-02-12" ] }

    :param list date: Either a string or a list of strings representing dates, e.g. [ "2018-02-01", "2018-02-12" ].
    :return: Gift, or collection of gifts.
    """

    date_0 = None
    date_1 = None

    # Make sure if no arguments given that something is returned.
    if ( isinstance( date, list ) and date == [] ) or date == '':
        return []

    if isinstance( date, list ):
        date_0 = datetime.strptime( date[ 0 ], '%Y-%m-%d' )
        date_1 = datetime.strptime( date[ 1 ], '%Y-%m-%d' )
        if date_0 > date_1:
            date_0, date_1 = date_1, date_0 + timedelta( hours=23, minutes=59, seconds=59 )
        else:
            date_0, date_1 = date_0, date_1 + timedelta( hours=23, minutes=59, seconds=59 )

    elif isinstance( date, str ):
        date_0 = datetime.strptime( date, '%Y-%m-%d' )
        date_1 = datetime.utcnow()
        if date_0 > date_1:
            return []

    gifts = GiftModel.query.join( TransactionModel, TransactionModel.gift_id == GiftModel.id )
    gifts = gifts.filter(
        and_( TransactionModel.date_in_utc >= date_0, TransactionModel.date_in_utc <= date_1 )
    )

    return gifts.all()


def get_gifts_by_given_to( given_to ):
    """Query to return gifts based on the given_to field on the model.

    If one given_to string is provided as a parameter Gifts with that value are returned. If a list of given_to
    strings is provided, all those matching Gifts will be returned. Does a bit of validation before the query, and
    makes sure the given_to strings are upper case.

    The post payload looks like: { "given_to": "NERF" } or { "given_to": [ "NERF", "ACTION" ] }

    :param dict given_to: Either a string or a list of strings for the given_to field.
    :return: Gift, or collection of gifts.
    """

    # Make sure if no arguments given that something is returned.
    if ( isinstance( given_to, list ) and given_to == [] ) or given_to == '':
        return []

    gifts = None
    if isinstance( given_to, list ):
        given_to = [ given_to_item.upper() for given_to_item in given_to ]
        gifts = GiftModel.query.filter( GiftModel.given_to.in_( given_to ) ).all()
    elif isinstance( given_to, str ):
        gifts = GiftModel.query.filter_by( given_to=given_to.upper() ).all()

    return gifts


def get_gifts_by_user_id( user_ids ):
    """Simple query to return gifts based on a user ID or list of user ID's.

    If the argument is an integer the gift corresponding to that user ID will be returned. For a list of user ID's
    the corresponding gifts will be returned.

    The post payload looks like: { "user_ids": 1 } or { "user_ids": [ 1, 2, 3, 4 ] }

    :param list user_ids: an integer, or a list of integers.
    :return: Gift, or collection of gifts.
    """

    # Make sure if no arguments given that something is returned.
    if ( isinstance( user_ids, list ) and user_ids == [] ) or user_ids == '':
        return []

    gifts = None
    if isinstance( user_ids, list ):
        gifts = GiftModel.query.filter( GiftModel.user_id.in_( user_ids ) ).all()
    elif isinstance( user_ids, int ):
        gifts = GiftModel.query.filter_by( user_id=user_ids ).all()

    return gifts


def get_gifts_by_searchable_ids( payload ):
    """An endpoint that returns gifts given a list of searchable IDs.

    :param payload: A list of searchable IDs.
    :return: A list of gifts.
    """

    if not payload:
        return []

    gifts = database.session.query( GiftModel ).filter( GiftModel.searchable_id.in_( payload ) )

    return gifts


def gifts_by_searchable_id_prefix( searchable_id_prefix ):
    """Return all gifts that match the searchable_id_prefix.

    :param searchable_id_prefix: A partial searchable ID.
    :return: Gifts that match the partial searchable ID.
    """

    try:
        sql_query = query_gift_like_uuid( searchable_id_prefix )
        results = database.session.execute( sql_query )
        return [ gift_tuple[ 0 ] for gift_tuple in results.fetchall() ]
    except SQLAlchemyError as error:
        raise error


def gift_build_notes( searchable_id ):
    """Given a Gift searchable ID find all transactions with notes and return a dictionary.

    :param searchable_id: A gift UUID searchable ID.
    :return: A dictionary of all notes of the attached transactions.
    """

    # Use the sql query to return gift ID so we can then use the model to get back all transactions for that ID.
    sql_query = query_gift_equal_uuid( 'id', searchable_id )
    results = database.session.execute( sql_query ).fetchone()
    if results:
        gift_id = results[ 0 ]
        gift = GiftModel.query.filter_by( id=gift_id ).one_or_none()
        notes = []
        for transaction in gift.transactions:
            if transaction.notes != '':
                notes.append(
                    {
                        'transaction_id': transaction.id,
                        'date_in_utc': transaction.date_in_utc.strftime( DATE_TIME_FORMAT ),
                        'notes': transaction.notes
                    }
                )
        return notes
    return False


def gift_update_note( searchable_id, payload ):
    """Update a gift with a new transaction containing the note.

    payload = {
        "enacted_by_agent_id": "5",
        "note": "Add this to the Gift please."
    }

    :param searchable_id: A gift UUID searchable ID.
    :param payload: The note to add to the gift as a separate transaction.
    :return: True if successfully updated, and False otherwise.
    """

    # Use the sql query to return gift ID so we can then use the model to get back all transactions for that ID.
    sql_query = query_gift_equal_uuid( 'id', searchable_id )
    results = database.session.execute( sql_query ).fetchone()
    if results:
        gift_id = results[ 0 ]

        enacted_by_agent = AgentModel.get_agent( 'Staff Member', 'user_id', payload[ 'agent_ultsys_id' ] )

        transaction_dict = {
            'gift_id': gift_id,
            'date_in_utc': datetime.utcnow().strftime( DATE_TIME_FORMAT ),
            'enacted_by_agent_id': enacted_by_agent.id,
            'type': 'Note',
            'status': 'Completed',
            'gross_gift_amount': Decimal( 0.00 ),
            'fee': Decimal( 0.00 ),
            'notes': payload[ 'note' ]
        }
        transaction_model = from_json( TransactionSchema(), transaction_dict )
        database.session.add( transaction_model.data )
        database.session.commit()
        return True
    return False
