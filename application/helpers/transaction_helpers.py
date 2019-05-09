"""A helper file that contains functions for modifying transactions. """
from datetime import datetime
from decimal import Decimal

from marshmallow.exceptions import ValidationError as MarshmallowValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound as SQLAlchemyORMNoResultFoundError

from application.exceptions.exception_model import ModelGiftNotFoundError
from application.exceptions.exception_model import ModelTransactionImproperFieldError
from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from application.helpers.sql_queries import query_gift_equal_uuid
from application.models.transaction import TransactionModel
from application.schemas.transaction import TransactionSchema

REQUIRED_FIELDS = [ 'enacted_by_agent_id', 'type', 'status' ]


def create_transaction( transaction_dict ):
    """Given a gift searchable ID create a transaction.

    The implementation uses transaction_dict[ 'gross_gift_amount' ] to update the current gross_gift_amount on
    the gift. If it should not be updated leave the field off the transaction_dict or set it to 0.00.

    :param transaction_dict: The transaction to create.
    :return:
    """

    sql_query = query_gift_equal_uuid( 'id', transaction_dict[ 'gift_searchable_id' ] )
    try:
        gift_model = database.session.execute( sql_query ).fetchone()

        # Get all the transactions on the gift and grab the current gross_gift_amount.
        transactions = TransactionModel.query.filter_by( gift_id=gift_model.id )\
            .order_by( TransactionModel.date_in_utc.desc() ).all()
        current_gross_gift_amount = Decimal( 0.00 )
        if transactions:
            current_gross_gift_amount = transactions[ 0 ].gross_gift_amount

    except SQLAlchemyORMNoResultFoundError as error:
        raise error

    if gift_model:

        reference_number = None
        transaction = TransactionModel.query \
            .filter_by( gift_id=gift_model.id ).filter_by( type='Gift' ).filter_by( status='Completed' ).one_or_none()
        if transaction:
            reference_number = transaction.reference_number

        scrub_transaction_dict( transaction_dict )

        date_in_utc = datetime.utcnow().strftime( '%Y-%m-%d %H:%M:%S' )
        transaction_dict[ 'date_in_utc' ] = date_in_utc
        transaction_dict[ 'gift_id' ] = gift_model.id
        transaction_dict[ 'gross_gift_amount' ] = \
            current_gross_gift_amount + Decimal( transaction_dict[ 'gross_gift_amount' ] )
        transaction_dict[ 'reference_number' ] = reference_number

        try:
            transaction_model = from_json( TransactionSchema(), transaction_dict, create=True )
            database.session.add( transaction_model.data )
            database.session.commit()
        except MarshmallowValidationError as error:
            raise error
        except SQLAlchemyError as error:
            database.session.rollback()
            raise error

        return transaction_model.data

    raise ModelGiftNotFoundError


def scrub_transaction_dict( transaction_dict ):
    """Scrubs the transaction dictionary to ensure that it contains the correct information and types.

    :param transaction_dict: The transaction payload
    :return:
    """
    for required_field in REQUIRED_FIELDS:
        if required_field not in transaction_dict or transaction_dict[ required_field ] == '':
            raise ModelTransactionImproperFieldError

    if transaction_dict[ 'type' ] == 'Note' and \
            ( 'notes' not in transaction_dict or transaction_dict[ 'notes' ] == '' ):
        raise ModelTransactionImproperFieldError
    if transaction_dict[ 'type' ] == 'Note' and transaction_dict[ 'status' ] != 'Completed':
        raise ModelTransactionImproperFieldError

    if 'fee' not in transaction_dict or \
            ( 'fee' in transaction_dict and transaction_dict[ 'fee' ] == '' ):
        transaction_dict[ 'fee' ] = Decimal( 0 )
    if 'gross_gift_amount' not in transaction_dict or \
            ( 'gross_gift_amount' in transaction_dict and transaction_dict[ 'gross_gift_amount' ] == '' ):
        transaction_dict[ 'gross_gift_amount' ] = Decimal( 0 )
