"""Module that handles the details of voiding a transaction."""
from flask import current_app

from application.exceptions.exception_critical_path import AdminBuildModelsPathError
from application.exceptions.exception_critical_path import AdminTransactionModelPathError
from application.flask_essentials import database
from application.helpers.braintree_api import init_braintree_credentials
from application.helpers.braintree_api import make_braintree_void
from application.helpers.model_serialization import from_json
from application.helpers.model_serialization import to_json
from application.models.agent import AgentModel
from application.models.gift import GiftModel
from application.models.transaction import TransactionModel
from application.schemas.braintree_sale import BraintreeSaleSchema
from application.schemas.transaction import TransactionSchema
# pylint: disable=bare-except
# flake8: noqa:E722


def void_transaction( payload ):
    """A function for voiding a Braintree transaction on a gift.

    Find the transaction in the database and get the Braintree transaction number. Configure the Braintree API and
    void the transaction through Braintree.

    payload = {
        "transaction_id": 1,
        "user_id": "1234",
        "transaction_notes": "Some transaction notes."
    }

    :param dict payload: A dictionary that provides information to void the transaction.
    :return:
    """

    # Retrieve the transaction that is to be voided.
    try:
        transaction_model = TransactionModel.query.filter_by( id=payload[ 'transaction_id' ] ).one()
    except:
        raise AdminTransactionModelPathError( 'voided' )

    try:
        braintree_id = transaction_model.reference_number
        # Need dictionary for schema, and schema.load will not include the gift_id by design.
        transaction_data = to_json( TransactionSchema(), transaction_model )
        transaction_json = transaction_data[ 0 ]
        transaction_json[ 'gift_id' ] = transaction_model.gift_id
        transaction_json[ 'notes' ] = payload[ 'transaction_notes' ]
    except:
        raise AdminBuildModelsPathError()

    # Generate Braintree void, where make_braintree_void() returns a Braintree voided transaction.
    init_braintree_credentials( current_app )

    transaction_void = make_braintree_void( braintree_id )

    # Need to attach the user who is doing the void.
    enacted_by_agent = AgentModel.get_agent( 'Staff Member', 'user_id', payload[ 'user_id' ] )
    transaction_json[ 'enacted_by_agent_id' ] = enacted_by_agent.id

    try:
        # Use BraintreeSaleSchema to populate gift and transaction dictionaries.
        braintree_schema = BraintreeSaleSchema()
        braintree_schema.context = { 'gift': {}, 'transaction': transaction_json }
        braintree_sale = braintree_schema.dump( transaction_void.transaction )
        transaction_json = braintree_sale.data[ 'transaction' ]

        gift_model = GiftModel.query.get( transaction_json[ 'gift_id' ] )
        gross_amount = gift_model.transactions[ 0 ].gross_gift_amount
        transaction_json[ 'gross_gift_amount' ] += gross_amount

        transaction_void_model = from_json( TransactionSchema(), transaction_json )
        database.session.add( transaction_void_model.data )
        database.session.commit()
        database.session.flush()
        transaction_json[ 'id' ] = transaction_void_model.data.id
    except:
        raise AdminBuildModelsPathError()

    return transaction_json
