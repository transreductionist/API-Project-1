"""Resource entry point for transaction endpoints."""
from flask import request
from nusa_filter_param_parser.nusa_filter_param_parser import build_filter_from_request_args
from nusa_jwt_auth import get_jwt_claims
from nusa_jwt_auth.restful import AdminResource

from application.controllers.transaction import build_transaction
from application.controllers.transaction import get_transactions_by_amount
from application.controllers.transaction import get_transactions_by_gifts
from application.controllers.transaction import get_transactions_by_ids
from application.controllers.transaction import get_transactions_for_csv
from application.exceptions.exception_jwt import JWTRequestError
from application.helpers.general_helper_functions import test_hex_string
from application.schemas.transaction import TransactionSchema
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use


class TransactionsByGift( AdminResource ):
    """Flask-RESTful resource endpoints for TransactionModel by a gift searchable ID."""

    def get( self, searchable_id ):
        """Simple endpoint to retrieve one row from table."""

        transaction = get_transactions_by_gifts( searchable_id )
        result = TransactionSchema( many=True ).dump( transaction ).data
        return result, 200


class TransactionsByGifts( AdminResource ):
    """Flask-RESTful resource endpoints for TransactionModel by gift searchable ID's."""

    def get( self ):
        """Simple endpoint to retrieve all rows from table."""

        transactions = get_transactions_by_gifts( None )
        result = TransactionSchema( many=True ).dump( transactions ).data
        return result, 200

    def post( self ):
        """Simple endpoint to return several rows from table given a list of gift searchable ID's."""

        transactions = get_transactions_by_gifts( request.json[ 'searchable_ids' ] )
        result = TransactionSchema( many=True ).dump( transactions ).data
        return result, 200


class TransactionsById( AdminResource ):
    """Flask-RESTful resource endpoints for TransactionModel by ID."""

    def get( self, transaction_id ):
        """Simple endpoint to retrieve one row from table."""

        transaction = get_transactions_by_ids( transaction_id )
        result = TransactionSchema().dump( transaction ).data
        return result, 200


class TransactionsByIds( AdminResource ):
    """Flask-RESTful resource endpoints for TransactionModel by ID's."""

    def get( self ):
        """Simple endpoint to retrieve all rows from table."""

        transactions = get_transactions_by_ids( transaction_ids=None )
        result = TransactionSchema( many=True ).dump( transactions ).data
        return result, 200

    def post( self ):
        """Simple endpoint to return several rows from table given a list of ID's."""

        transactions = get_transactions_by_ids( request.json[ 'transaction_ids' ] )
        result = TransactionSchema( many=True ).dump( transactions ).data
        return result, 200


class TransactionsByGrossGiftAmount( AdminResource ):
    """Flask-RESTful resource endpoints for TransactionModel by gross gift amount."""

    def post( self ):
        """Endpoint returns query against gross gift amounts.

        Can provide transactions for gross gift amounts greater than, or greater than or less than, the specified
        amount or amounts.
        """

        transactions = get_transactions_by_amount( request.json[ 'gross_gift_amount' ] )
        result = TransactionSchema( many=True ).dump( transactions ).data
        return result, 200


class TransactionBuild( AdminResource ):
    """Flask-RESTful resource endpoints for creating a Transaction attached to a specified gift."""

    def post( self ):
        """Endpoint builds a transaction for a specified gift searchable ID.

        :return: A transaction.
        """

        # Authenticate the admin user.
        payload = request.json
        try:
            agent_ultsys_id = get_jwt_claims()[ 'ultsys_id' ]
        except KeyError:
            raise JWTRequestError()

        if not test_hex_string( payload[ 'gift_searchable_id' ] ):
            raise TypeError

        transaction = build_transaction( payload, agent_ultsys_id )

        result = TransactionSchema().dump( transaction ).data
        return result, 200


class TransactionsForCSV( AdminResource ):
    """Build the CSV file for combined transaction and gift data to export."""

    def get( self ):
        """The GET endpoint to get the transactions for building the CSV."""

        query_terms = build_filter_from_request_args( request.args )

        url = get_transactions_for_csv( query_terms )
        return { 'url': url }, 200
