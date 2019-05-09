"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
import copy

from nusa_filter_param_parser.build_query_set import query_set
from nusa_filter_param_parser.build_query_set import query_set_with_relation
from sqlalchemy import alias
from sqlalchemy import desc
from sqlalchemy import func

from application.helpers.manage_paginate import convert_into_page
from application.models.gift import GiftModel
from application.models.transaction import TransactionModel
from application.schemas.transaction import TransactionSchema

TRANSACTION_FIELDS = [ column.key for column in TransactionSchema.Meta.model.__table__.columns ]


def build_gifts_from_query( query_terms, page_information, sort_information ):
    """An endpoint that returns gifts filtered by the query terms, paginated, and sorted.

    Here is an example of query, paginate and sort terms as they might appear in the URL: &given_to=NERF&user_id=4
        &gross_gift_amount=20&type=Gift&status=Accepted&sort=id:desc&rows_per_page=25&page_number=3

    Notice that the endpoint accepts both GiftModel and TransactionModel fields without a prefix such as
    gift.method_used. The GiftModel and TransactionModel fields are disjoint.

    :param query_terms: Query terms for gifts and attached transactions
    :param page_information: Paginate information
    :param sort_information: Sort information
    :return: paginated, filtered, sorted gifts
    """

    # Build separate filters for the gifts and the transactions.
    filters = build_filters( query_terms )
    gifts_query = GiftModel.query
    if filters[ 'gift' ]:

        # If max_date_in_utc is set in filters[ 'gifts' ] then an aggregate needs to be composed.
        # If this is the case del the filter item before building the base gift query.
        max_date_in_utc = False
        for index, filter_item in enumerate( filters[ 'gift' ] ):
            if filter_item[ 0 ] == 'max_date_in_utc':
                max_date_in_utc = True
                del filters[ 'gift' ][ index ]
                break

        gifts_query = query_set( GiftModel, gifts_query, filters[ 'gift' ] )

        # Build the aggregate.
        if max_date_in_utc:
            transactions = alias(
                TransactionModel.query.with_entities(
                    TransactionModel.gift_id, func.max( TransactionModel.date_in_utc ).label( 'max_date_in_utc' )
                ).group_by( TransactionModel.gift_id ).with_entities(
                    TransactionModel.gift_id, func.max( TransactionModel.date_in_utc ).label( 'max_date_in_utc' )
                )
            )
            gifts_query = gifts_query.\
                join( transactions, transactions.c.transaction_gift_id == GiftModel.id ).\
                order_by( desc( transactions.c.max_date_in_utc ) )

    # Handle sorting if requested.
    for sort_by in sort_information:
        if sort_by[ 'value' ] == 'desc':
            gifts_query = gifts_query.order_by( getattr( GiftModel, sort_by[ 'attribute' ] ).desc() )
        else:
            gifts_query = gifts_query.order_by( getattr( GiftModel, sort_by[ 'attribute' ] ).asc() )

    gifts_query = query_set_with_relation(
        gifts_query, TransactionModel, GiftModel.transactions, filters[ 'transaction' ]
    )

    if page_information:
        gifts = convert_into_page( gifts_query, page_information )
    else:
        gifts = gifts_query.all()

    return gifts


def build_filters( query_terms ):
    """Given the gift query terms separate out gift & transaction terms and build filters.

    The query_terms may have transaction query terms as well. Separate out these terms, building separate
    gift and transaction query terms. From these 2 dictionaries build specific filters for the gift and the
    transactions.


    :param query_terms:
    :return: filters
    """

    transaction_query_terms = {}
    query_terms_copy = copy.deepcopy( query_terms )
    for query_term_key, query_term_value in query_terms_copy.items():
        # Don't query by transaction ID.
        if query_term_key in TRANSACTION_FIELDS and query_term_key != 'id':
            transaction_query_terms[ query_term_key ] = query_term_value
            del query_terms[ query_term_key ]

    transaction_filters = []
    if transaction_query_terms:
        for attribute, operator_value in transaction_query_terms.items():
            for operator, value in operator_value.items():
                transaction_filters.append( ( attribute, operator, value ) )

    gift_filters = []
    if query_terms:
        for attribute, operator_value in query_terms.items():
            for operator, value in operator_value.items():
                gift_filters.append( ( attribute, operator, value ) )

    return { 'transaction': transaction_filters, 'gift': gift_filters }
