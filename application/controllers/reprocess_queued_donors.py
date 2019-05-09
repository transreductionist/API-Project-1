"""Resources entry point to make a Braintree sale."""
from flask import current_app

from application.helpers.caging import redis_queue_caging
from application.helpers.general_helper_functions import validate_user_payload
from application.helpers.model_serialization import to_json
from application.models.queued_donor import QueuedDonorModel
from application.models.transaction import TransactionModel
from application.schemas.queued_donor import QueuedDonorSchema
from application.schemas.transaction import TransactionSchema
# pylint: disable=bare-except
# flake8: noqa:E722


def reprocess_queued_donors( payload=None ):
    """Reprocess existing queued donors."""

    if payload:
        queued_donors = QueuedDonorModel.query.filter( QueuedDonorModel.id.in_( payload[ 'queued_donor_ids' ] ) )
    else:
        queued_donors = QueuedDonorModel.query.all()

    jobs = []
    for queued_donor_model in queued_donors:
        queued_donor_dict = to_json( QueuedDonorSchema(), queued_donor_model ).data
        queued_donor_dict[ 'gift_id' ] = queued_donor_model.gift_id
        queued_donor_dict[ 'queued_donor_id' ] = queued_donor_model.id
        queued_donor_dict[ 'category' ] = 'queued'
        queued_donor_dict.pop( 'id' )

        # May be multiple transactions for a gift, e.g. check with a Gift and Deposit to Bank.
        transaction_models = TransactionModel.query.filter_by( gift_id=queued_donor_model.gift_id ).all()
        transactions = []
        for transaction_model in transaction_models:
            if transaction_model.type in [ 'Gift', 'Deposit to Bank' ]:
                transaction_dict = to_json( TransactionSchema(), transaction_model ).data
                transactions.append( transaction_dict )

        # Caging expects a user dictionary that has a user something like: { user_address:{}, 'billing_address':{} }.
        # Put the queued donor dictionary in this form.
        queued_donor_dict = validate_user_payload( queued_donor_dict )

        # Once on the queue it is out of our hands, but may fail on arguments to queue().
        try:
            job = redis_queue_caging.queue(
                queued_donor_dict, transactions, current_app.config[ 'ENV' ]
            )
            jobs.append( ( queued_donor_dict[ 'queued_donor_id' ], job.get_id() ) )
        except:
            jobs.append( ( queued_donor_dict[ 'queued_donor_id' ], 'failed' ) )

    response = None
    if jobs:
        response = { 'reprocessed_jobs': jobs }

    return response
