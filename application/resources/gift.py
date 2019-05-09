"""The Resources entry point for returning gifts"""
import copy

from flask import jsonify
from flask import request
from flask_api import status
from nusa_filter_param_parser.nusa_filter_param_parser import build_filter_from_request_args
from nusa_jwt_auth import get_jwt_claims
from nusa_jwt_auth.restful import AdminResource

from application.controllers.gift import get_gifts
from application.controllers.gift import get_gifts_by_date
from application.controllers.gift import get_gifts_by_given_to
from application.controllers.gift import get_gifts_by_searchable_ids
from application.controllers.gift import get_gifts_by_user_id
from application.controllers.gift import gift_build_notes
from application.controllers.gift import gift_update_note
from application.controllers.gift import gifts_by_searchable_id_prefix
from application.exceptions.exception_jwt import JWTRequestError
from application.exceptions.exception_uuid import UUIDLessThanFiveCharsError
from application.helpers.general_helper_functions import test_hex_string
from application.helpers.manage_paginate import transform_data
from application.schemas.gift import GiftSchema
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use


class Gifts( AdminResource ):
    """Flask-RESTful resource endpoints GiftModel Gifts."""

    def get( self ):
        """Simple endpoint to retrieve all rows from table."""

        query_terms = build_filter_from_request_args( request.args )
        link_header_query_terms = None
        # Build the page and sort information from the filter results on the query string.
        # Delete these keys and pass along only the model filter/search terms.
        page_information = {}
        sort_information = []
        if query_terms:
            page_information = {}
            if 'paginate' in query_terms and query_terms[ 'paginate' ]:
                page_information = {
                    'page_number': query_terms[ 'paginate' ][ 'page_number' ],
                    'rows_per_page': query_terms[ 'paginate' ][ 'rows_per_page' ]
                }
                del query_terms[ 'paginate' ]

            link_header_query_terms = copy.deepcopy( query_terms )

            if 'sort' in query_terms and query_terms[ 'sort' ]:
                sort_information = query_terms[ 'sort' ]
                del query_terms[ 'sort' ]

        gifts = get_gifts( query_terms, page_information=page_information, sort_information=sort_information )

        if page_information:
            transformed_data = transform_data(
                'donation/gifts',
                link_header_query_terms,
                gifts,
                GiftSchema
            )
            response = jsonify( transformed_data[ 'page' ] )
            response.headers[ 'Link' ] = transformed_data[ 'link-header' ]
            response.status_code = status.HTTP_200_OK
            return response

        schema = GiftSchema( many=True )
        result = schema.dump( gifts ).data
        return result, status.HTTP_200_OK

    def post( self ):
        """Simple endpoint to return several rows from table given a list of ID's."""
        if not request.json[ 'searchable_ids' ]:
            return []

        gifts = get_gifts_by_searchable_ids( request.json[ 'searchable_ids' ] )
        schema = GiftSchema( many=True )
        result = schema.dump( gifts ).data
        return result, status.HTTP_200_OK


class GiftsByDate( AdminResource ):
    """Flask-RESTful resource endpoints GiftModel for all Gifts by attached Transaction date."""

    def post( self ):
        """Endpoint to return several Gifts from table given a date or a range of dates for attached Transactions."""
        gifts = get_gifts_by_date( request.json[ 'date' ] )
        # We are using dump many=True and so if a single gift returned need to put it in a list.

        schema = GiftSchema( many=True )
        result = schema.dump( gifts ).data
        return result, status.HTTP_200_OK


class GiftsByGivenTo( AdminResource ):
    """Flask-RESTful resource endpoints GiftModel for all Gifts by given_to."""

    def post( self ):
        """Endpoint to return several Gifts from table given a given_to."""
        gifts = get_gifts_by_given_to( request.json[ 'given_to' ] )
        schema = GiftSchema( many=True )
        result = schema.dump( gifts ).data
        return result, status.HTTP_200_OK


class GiftByUserId( AdminResource ):
    """Flask-RESTful resource endpoints GiftModel for retrieval by user ID."""

    def get( self, user_id ):
        """Endpoint to return several Gifts from table given a user ID."""
        gift = get_gifts_by_user_id( user_id )
        schema = GiftSchema( many=True )
        result = schema.dump( gift ).data
        return result, status.HTTP_200_OK

    def post( self ):
        """Endpoint to return several Gifts from table given a list of user ID's."""
        gifts = get_gifts_by_user_id( request.json[ 'user_ids' ] )
        schema = GiftSchema( many=True )
        result = schema.dump( gifts ).data
        return result, status.HTTP_200_OK


class GiftsByPartialSearchableId( AdminResource ):
    """Flask-RESTful resource endpoints GiftModel for retrieval of searchable ID by prefix."""

    def get( self, searchable_id_prefix ):
        """Endpoint to return several Gifts from table given the prefix of a searchable ID."""

        # Sanitize incoming partial UUID to only hex characters and ensure length is at least 5 characters.
        if not test_hex_string( searchable_id_prefix ) or len( searchable_id_prefix ) < 5:
            raise TypeError
        return gifts_by_searchable_id_prefix( searchable_id_prefix ), status.HTTP_200_OK


class GiftUpdateNote( AdminResource ):
    """Flask-RESTful resource endpoints for updating notes on a gift."""

    def get( self, searchable_id ):
        """Endpoint to return all transactions notes on the identified Gift."""
        if not test_hex_string( searchable_id ):
            raise TypeError

        gift_notes = gift_build_notes( searchable_id )
        if gift_notes or gift_notes == []:
            return gift_notes, status.HTTP_200_OK
        return None, status.HTTP_404_NOT_FOUND

    def put( self, searchable_id ):
        """Endpoint to Add a note to the identified Gift."""

        # Authenticate the admin user.
        payload = request.get_json()
        try:
            payload[ 'agent_ultsys_id' ] = get_jwt_claims()[ 'ultsys_id' ]
        except KeyError:
            raise JWTRequestError()

        if not test_hex_string( searchable_id ):
            raise UUIDLessThanFiveCharsError
        if gift_update_note( searchable_id, request.get_json() ):
            return None, status.HTTP_200_OK

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR
