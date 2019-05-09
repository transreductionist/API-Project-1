"""Module that allows administrative staff to correct and/or reallocate a gift."""
import datetime
import logging
from decimal import Decimal

import braintree
from flask import current_app

from application.exceptions.exception_critical_path import AdminFindGiftPathError
from application.exceptions.exception_critical_path import AdminTransactionModelPathError
from application.exceptions.exception_critical_path import AdminUpdateSubscriptionPathError
from application.flask_essentials import database
from application.helpers.braintree_api import handle_braintree_errors
from application.helpers.braintree_api import init_braintree_credentials
from application.helpers.model_serialization import from_json
from application.models.agent import AgentModel
from application.models.gift import GiftModel
from application.models.transaction import TransactionModel
from application.schemas.transaction import TransactionSchema
# pylint: disable=bare-except
# flake8: noqa:E722


def correct_gift():
    """A function for correcting a gift.

    :return: GiftModel
    """

    gift_model = GiftModel(
        user_id=1,
        campaign_id=None,
        customer_id=None,
        method_used=1,
        sourced_from_agent_id=1,
        given_to='NERF',
        recurring_subscription=None
    )

    return gift_model


def reallocate_subscription( recurring_subscription_id, reallocate_to ):
    """A function for reallocating a Braintree gift subscription.

    :param recurring_subscription_id: The Braintree subscription ID from the gift.
    :param reallocate_to: The account to reallocate the donation to.
    :return: Braintree subscription
    """

    # Configure Braintree.
    init_braintree_credentials( current_app )

    merchant_account_id = {
        'NERF': current_app.config[ 'NUMBERSUSA' ],
        'ACTION': current_app.config[ 'NUMBERSUSA_ACTION' ]
    }

    # This is an administrative function and we allow them to grab a default payment method.
    subscription = braintree.Subscription.find( recurring_subscription_id )

    # Getting this far, we can now update the subscription to the new plan and merchant account ID as required.
    # The original Braintree transaction maintains the same merchant account ID for historical significance.
    # The original Braintree transaction that is reallocated will have the new subscription plan ID.
    # New Braintree transactions from the subscription will have new merchant account ID/subscription plan ID.
    braintree_subscription = braintree.Subscription.update(
        recurring_subscription_id,
        {
            'id': recurring_subscription_id,
            'payment_method_token': subscription.payment_method_token,
            'plan_id': merchant_account_id[ reallocate_to ],
            'merchant_account_id': merchant_account_id[ reallocate_to ]
        }
    )
    if not braintree_subscription.is_success:
        errors = handle_braintree_errors( braintree_subscription )
        logging.exception( AdminUpdateSubscriptionPathError( errors=errors ).message )

    return braintree_subscription


def correct_transaction( transaction_model, gift_model, enacted_by_agent_model ):
    """A function for creating correction (transaction).

     The gift might be reallocated to a different organization, e.g. NERF, ACTION, or SUPPORT.

    :param transaction_model: The incomplete TransactionModel.
    :param gift_model: The associated GiftModel.
    :param enacted_by_agent_model: The agent enacting the correction as AgentModel.
    :return: The completed TransactionModel
    """

    try:
        # Need original transaction for reference number
        transaction = TransactionModel.query \
            .filter_by( gift_id=gift_model.id ).filter_by( type='Gift' ).filter_by( status='Completed' ).one()
        transaction_model.gift_id = gift_model.id
        transaction_model.date_in_utc = datetime.datetime.utcnow().strftime( '%Y-%m-%d %H:%M:%S' )
        transaction_model.enacted_by_agent_id = enacted_by_agent_model.id if enacted_by_agent_model else None
        transaction_model.type = 'Correction'
        transaction_model.status = 'Completed'
        transaction_model.reference_number = transaction.reference_number if transaction else None
        database.session.add_all( [ transaction_model, gift_model ] )
        database.session.commit()
    except:
        database.session.rollback()
        raise AdminTransactionModelPathError( where='parent' )

    return transaction_model, gift_model
