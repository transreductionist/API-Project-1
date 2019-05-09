"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
import uuid
from decimal import Decimal

from flask import current_app
from nusa_filter_param_parser.build_query_set import query_set
from s3_web_storage.web_storage import WebStorage
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import aliased

from application.flask_essentials import database
from application.helpers.build_output_file import build_flat_bytesio_csv
from application.helpers.gift_helpers import build_filters
from application.helpers.transaction_helpers import create_transaction
from application.models.agent import AgentModel
from application.models.gift import GiftModel
from application.models.method_used import MethodUsedModel
from application.models.transaction import TransactionModel


def get_transactions_by_gifts( gift_searchable_ids ):
    """Simple query to return transactions based on the gift searchable ID or ID's provided.

    If there is no gift searchable ID all transactions will be returned. If a gift searchable ID is given all
    transactions attached to that searchable ID will be returned. Finally, if a list of gift searchable ID's are
    provided all transactions attached to those gifts are returned.

    The payload looks like:
    { "searchable_ids": [ "ddd9a1e8-8100-457f-b52c-3871ee4920b7", "ddd9a1e8-8100-457f-b52c-3871ee4920b7" ] }
    or
    { "searchable_ids": "ddd9a1e8-8100-457f-b52c-3871ee4920b7" }

    :param list gift_searchable_ids: A list of gift searchable ID's, a string, or None.
    :return: All transactions attached to the gift or gifts.
    """

    if isinstance( gift_searchable_ids, list ) and gift_searchable_ids != []:
        gift_searchable_ids = [ uuid.UUID( gift_searchable_id ) for gift_searchable_id in gift_searchable_ids ]
        gifts = GiftModel.query\
            .filter( GiftModel.searchable_id.in_( gift_searchable_ids ) )\
            .all()
        transactions = [ transaction for gift in gifts for transaction in gift.transactions ]
    elif isinstance( gift_searchable_ids, str ):
        gift = GiftModel.query\
            .filter_by( searchable_id=uuid.UUID( gift_searchable_ids ) )\
            .one_or_none()
        transactions = []
        if gift:
            transactions = gift.transactions
    else:
        transactions = TransactionModel.query.all()
    return transactions


def get_transactions_by_ids( transaction_ids ):
    """Simple query to return transactions based on transaction ID or ID's provided.

    If there is no transaction ID all transactions will be returned. If a transaction ID is given that transaction
    will be returned. Finally, if a list of transaction ID's are provided all those transactions will be returned.

    The payload looks like: { "transaction_ids": [ 1, 2, 3 ] } or { "transaction_ids": 1 }

    :param list transaction_ids: A list of transaction ID's, an integer, or None.
    :return: All transactions requested.
    """

    if isinstance( transaction_ids, list ) and transaction_ids != []:
        transactions = TransactionModel.query\
            .filter( TransactionModel.id.in_( transaction_ids ) )\
            .all()
    elif isinstance( transaction_ids, int ):
        transactions = TransactionModel.query\
            .filter_by( id=transaction_ids )\
            .first()
    else:
        transactions = TransactionModel.query.all()
    return transactions


def get_transactions_by_amount( gross_gift_amount ):
    """Query to return transactions based on a specified gross gift amount.

    If a list of amounts is provided, Transactions are searched for the given amount range. If one amount is provided
    as a parameter, all Transactions are returned greater than or equal to that amount. If a list of amounts are
    specified these are used to build a range query on that amount. If an empty list is passed then all transactions
    are returned.

    The post payload looks like: { "gross_gift_amount": "1000.00" } or { "gross_gift_amount": [ "25.00", "50.00" ] }

    :param list gross_gift_amount: List of strings or a string representing gross gift amounts.
    :return: Gift, or collection of gifts.
    """

    transactions = None
    if isinstance( gross_gift_amount, list ) and gross_gift_amount != []:
        gross_gift_amount_0 = Decimal( gross_gift_amount[ 1 ] )
        gross_gift_amount_1 = Decimal( gross_gift_amount[ 0 ] )
        if gross_gift_amount_0 > gross_gift_amount_1:
            gross_gift_amount_0, gross_gift_amount_1 = gross_gift_amount_1, gross_gift_amount_0

        transactions = TransactionModel.query\
            .filter(
                and_(
                    TransactionModel.gross_gift_amount >= gross_gift_amount_0,
                    TransactionModel.gross_gift_amount <= gross_gift_amount_1
                )
            )\
            .all()
    elif isinstance( gross_gift_amount, str ) and gross_gift_amount != '':
        gross_gift_amount_0 = Decimal( gross_gift_amount )
        transactions = TransactionModel.query\
            .filter( TransactionModel.gross_gift_amount >= gross_gift_amount_0 )\
            .all()
    else:
        transactions = TransactionModel.query.all()

    return transactions


def build_transaction( transaction_dict, agent_ultsys_id ):
    """The controller to build a transaction for a gift with searchable ID.

    :param transaction_dict: The transaction dictionary to use to build the model.
    :param agent_ultsys_id: The agent ultsys ID to be converted to the Agent ID primary key.
    :return: A transaction.
    """
    enacted_by_agent = AgentModel.get_agent( 'Staff Member', 'user_id', agent_ultsys_id )
    transaction_dict[ 'enacted_by_agent_id' ] = enacted_by_agent.id
    transaction = create_transaction( transaction_dict )

    return transaction


def get_transactions_for_csv( query_terms ):
    """
    Query all transactions and call a function to save them into a .csv file, then put the file into S3.
    :return: Return a signed URL that users can download from S3
    """

    try:
        sourced_from_agent = aliased( AgentModel )
        enacted_by_agent = aliased( AgentModel )
        method_used = aliased( MethodUsedModel )

        query = database.session.query(
            GiftModel.id,
            GiftModel.searchable_id,
            GiftModel.user_id,
            GiftModel.method_used_id,
            method_used.name,
            GiftModel.given_to,
            GiftModel.recurring_subscription_id,
            TransactionModel.date_in_utc,
            TransactionModel.receipt_sent_in_utc,
            enacted_by_agent.id,
            enacted_by_agent.name,
            TransactionModel.type,
            TransactionModel.status,
            TransactionModel.reference_number,
            TransactionModel.gross_gift_amount,
            TransactionModel.fee,
            TransactionModel.notes
        ). \
            join( TransactionModel, GiftModel.id == TransactionModel.gift_id ). \
            join( sourced_from_agent, GiftModel.sourced_from_agent_id == sourced_from_agent.id ). \
            join( enacted_by_agent, TransactionModel.enacted_by_agent_id == enacted_by_agent.id ). \
            join( method_used, GiftModel.method_used_id == method_used.id )

        if query_terms:
            filters = build_filters( query_terms )
            if 'gift' in filters and filters[ 'gift' ]:
                query = query_set( GiftModel, query, filters[ 'gift' ] )
            if 'transaction' in filters and filters[ 'transaction' ]:
                query = query_set( TransactionModel, query, filters[ 'transaction' ] )

        results = query.all()

    except SQLAlchemyError as error:
        raise error

    header = [
        'gift_id', 'searchable_gift_id', 'user_id', 'method_used_id', 'method_used_name', 'given_to',
        'recurring_subscription_id', 'transaction_date_in_utc', 'receipt_sent_in_utc', 'transaction_agent_id',
        'transaction_agent_name', 'transaction_type', 'transaction_status', 'reference_number',
        'transaction_gross_amount', 'transaction_fee', 'transaction_notes'

    ]
    WebStorage.init_storage(
        current_app, current_app.config[ 'AWS_CSV_FILES_BUCKET' ],
        current_app.config[ 'AWS_CSV_FILES_PATH' ]
    )
    file_name = build_flat_bytesio_csv( results, header, 'transactions', True )

    url = WebStorage.generate_presigned_url(
        current_app.config[ 'AWS_CSV_FILES_BUCKET' ],
        current_app.config[ 'AWS_CSV_FILES_PATH' ] + file_name
    )
    return url
