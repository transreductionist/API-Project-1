"""Module that handles the refund of a Braintree transaction."""
from flask import current_app

from application.exceptions.exception_critical_path import AdminBuildModelsPathError
from application.exceptions.exception_critical_path import AdminTransactionModelPathError
from application.flask_essentials import database
from application.helpers.braintree_api import init_braintree_credentials
from application.helpers.braintree_api import make_braintree_refund
from application.helpers.model_serialization import from_json
from application.helpers.model_serialization import to_json
from application.models.agent import AgentModel
from application.models.gift import GiftModel
from application.models.transaction import TransactionModel
from application.schemas.braintree_sale import BraintreeSaleSchema
from application.schemas.transaction import TransactionSchema
# pylint: disable=bare-except
# flake8: noqa:E722


def refund_transaction( payload ):
    """A function for refunding a Braintree transaction on a gift.

    Find the transaction in the database and get the Braintree transaction number. Configure the Braintree API and
    make the refund through Braintree.

    payload = {
        "transaction_id": 1,
        "amount": "0.01",
        "transaction_notes": "Some transaction notes."
    }

    :param dict payload: A dictionary that provides information to make the refund.
    :return:
    :raises MarshmallowValidationError: If Marshmallow throws a validation error.
    :raises SQLAlchemyError: General SQLAlchemy error.
    :raises SQLAlchemyORMNoResultFoundError: The ORM didn't find the table row.
    """

    # Retrieve the transaction that is to be refunded and raise an exception if not found.
    # Don't try to continue to Braintree without a valid reference number.
    try:
        transaction_model = TransactionModel.query.filter_by( id=payload[ 'transaction_id' ] ).one()
    except:
        raise AdminTransactionModelPathError( where='parent' )

    transactions = TransactionModel.query.filter_by( gift_id=transaction_model.gift_id ).all()
    current_balance = transactions[ -1 ].gross_gift_amount

    # If the model cannot be built do not continue to Braintree.
    # Raise an exception.
    try:
        # Build transaction dictionary for schema.
        braintree_id = transaction_model.reference_number
        transaction_data = to_json( TransactionSchema(), transaction_model )
        transaction_json = transaction_data.data
        transaction_json[ 'gift_id' ] = transaction_model.gift_id
        transaction_json[ 'notes' ] = payload[ 'transaction_notes' ]
    except:
        raise AdminBuildModelsPathError()

    # Configure Braintree so we can generate a refund.
    init_braintree_credentials( current_app )

    # Function make_braintree_refund() returns: a Braintree refund transaction.
    transaction_refund = make_braintree_refund( braintree_id, payload[ 'amount' ], current_balance )

    # Need to attach the user who is doing the reallocation.
    enacted_by_agent = AgentModel.get_agent( 'Staff Member', 'user_id', payload[ 'user_id' ] )
    transaction_json[ 'enacted_by_agent_id' ] = enacted_by_agent.id

    try:
        # Use BraintreeSaleSchema to populate gift and transaction dictionaries.
        braintree_schema = BraintreeSaleSchema()
        braintree_schema.context = {
            'gift': {},
            'transaction': transaction_json
        }
        braintree_sale = braintree_schema.dump( transaction_refund.transaction )
        transaction_json = braintree_sale.data[ 'transaction' ]
        transaction_json.pop( 'id' )

        gift_model = GiftModel.query.get( transaction_json[ 'gift_id' ] )
        gross_amount = gift_model.transactions[ 0 ].gross_gift_amount
        transaction_json[ 'gross_gift_amount' ] += gross_amount

        transaction_refund_model = from_json( TransactionSchema(), transaction_json )
        database.session.add( transaction_refund_model.data )
        database.session.commit()
        database.session.flush()
        transaction_json[ 'id' ] = transaction_refund_model.data.id
    except:
        raise AdminBuildModelsPathError()

    return transaction_json
