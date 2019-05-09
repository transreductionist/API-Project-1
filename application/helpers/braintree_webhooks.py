"""Core code that manages NUSA donor subscriptions using Braintree webhooks."""
import logging
from datetime import datetime
from decimal import Decimal

import braintree
from flask import current_app
from sqlalchemy import or_

from application.exceptions.exception_critical_path import AdminBuildModelsPathError
from application.exceptions.exception_critical_path import AdminFindGiftPathError
from application.exceptions.exception_critical_path import BraintreeWebhooksCagedDonorPathError
from application.exceptions.exception_critical_path import BraintreeWebhooksGiftThankYouPathError
from application.exceptions.exception_critical_path import BraintreeWebhooksIDPathError
from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from application.helpers.model_serialization import to_json
from application.models.agent import AgentModel
from application.models.caged_donor import CagedDonorModel
from application.models.gift import GiftModel
from application.models.gift_thank_you_letter import GiftThankYouLetterModel
from application.models.method_used import MethodUsedModel
from application.models.queued_donor import QueuedDonorModel
from application.schemas.caged_donor import CagedDonorSchema
from application.schemas.gift import GiftSchema
from application.schemas.queued_donor import QueuedDonorSchema
from application.schemas.transaction import TransactionSchema
# pylint: disable=bare-except
# flake8: noqa:E722


def manage_subscription( webhook_notification, gateway ):
    """Manage the several kinds of subscription webhooks we have enabled triggers for.

    Subscription webhooks which are managed:
        1. braintree.WebhookNotification.Kind.SubscriptionChargedSuccessfully
        2. braintree.WebhookNotification.Kind.SubscriptionChargedUnsuccessfully
        3. braintree.WebhookNotification.Kind.SubscriptionExpired
        4. braintree.WebhookNotification.Kind.SubscriptionWentPastDue

    Subscription webhooks which are not managed:
        1. braintree.WebhookNotification.Kind.SubscriptionCanceled
        2. braintree.WebhookNotification.Kind.SubscriptionTrialEnded
        3. braintree.WebhookNotification.Kind.SubscriptionWentActive

    When testing in the Sandbox ensure recurring billing in settings is set to prorate on upgrade and downgrade. When
    you want to trigger a subscription edit it and change the amount. On saving the subscription will trigger and
    charge the prorated amount. Keep in mind that the endpoint can take some time to receive the update. Be patient.
    On one update to the amount it took 3:30 minutes to fire.

    :param webhook_notification: The Braintree notification object.
    :param gateway: The Braintree class instance API.
    :return: User, transaction, gift models as dictionaries
    """

    # Handle associating the user_id and customer_id correctly. On the sale the Braintree customer ID is attached to
    # the gift. The donor is caged and either sent to the caged donor table ( gift does not get Ultsys user ID ) or
    # the gift is updated with an Ultsys user ID. We need to handle these 2 possible situations in the subscription
    # webhook.

    # If this is the first process for a subscription, and the initial online sale handled elsewhere, then bypass.
    if len( webhook_notification.subject[ 'subscription' ][ 'transactions' ] ) <= 1:
        return None

    # Process the webhook. Begin by getting some needed parameters.
    agent_id = get_agent_id()
    status = get_webhook_status( webhook_notification )
    recurring_subscription_id = webhook_notification.subject[ 'subscription' ][ 'id' ]
    braintree_id = webhook_notification.subject[ 'subscription' ][ 'transactions' ][ 0 ][ 'id' ]

    # Get the customer ID so we can find the initial gift.
    customer_id = get_braintree_customer_id( gateway, braintree_id )
    gift_with_customer_id = get_gift_with_customer_id( customer_id )

    # Build the new gift and transaction.
    transaction_dict = create_gift_and_transaction(
        gift_with_customer_id, webhook_notification, recurring_subscription_id, agent_id, status
    )

    # The user may still be caged, or even stuck in the redis queue.
    # In this case add a new entry for them for this gift.
    user_id = gift_with_customer_id.user_id
    if user_id in [ -1, -2 ]:
        caged_queued_donor_model = resolve_user( gift_with_customer_id )
        manage_queued_caged_donor(
            caged_queued_donor_model,
            transaction_dict[ 'gift_id' ],
            transaction_dict[ 'gift_searchable_id' ]
        )

    # Update the gift thank you letter table if required.
    if transaction_dict:
        try:
            # If the gift amount >= $100 ( current threshold ), add to gift_thank_you_letter table
            gross_gift_amount = Decimal( transaction_dict[ 'gross_gift_amount' ] )
            if gross_gift_amount >= Decimal( current_app.config[ 'THANK_YOU_LETTER_THRESHOLD' ] ):
                database.session.add( GiftThankYouLetterModel( gift_id=transaction_dict[ 'gift_id' ] ) )
        except:  # noqa: E722
            database.session.rollback()
            logging.exception( BraintreeWebhooksGiftThankYouPathError().message )

    try:
        database.session.commit()
    except:  # noqa: E722
        database.session.rollback()
        logging.exception( AdminBuildModelsPathError().message )

    return transaction_dict


def get_agent_id():
    """Get the agent ID for the Donate API.

    :return: agent_id
    """

    agent = AgentModel.get_agent( 'Organization', 'name', 'Donate API' )
    agent_id = agent.id

    return agent_id


def get_braintree_customer_id( gateway, braintree_id ):
    """Get the Braintree customer ID so that we can find the gift.

    :param gateway: The gateway for accessing the Braintree API.
    :param braintree_id: The Braintree transaction ID.
    :return: customer_id
    """

    # It is possible that the transaction for the braintree_id is not found. For example, in the Sandbox certain
    # deleted subscriptions may still fire. In this case raise an error.
    try:
        transaction = gateway.transaction.find( braintree_id )
        customer_id = transaction.customer_details.id
        return customer_id
    except:  # noqa: E722
        raise BraintreeWebhooksIDPathError( type_id=braintree_id )


def get_gift_with_customer_id( customer_id ):
    """Given a Braintree customer ID find its gift.

    :param customer_id: Braintree customer ID.
    :return: GiftModel for that customer ID.
    """

    try:
        # Find if a gift exists with the customer ID. We only have to look at Online or administrative online sales.
        # The customer_id is renewed on each sale and so should be unique to that donation.
        id_online = MethodUsedModel.get_method_used( 'name', 'Web Form Credit Card' ).id
        id_credit_card = MethodUsedModel.get_method_used( 'name', 'Admin-Entered Credit Card' ).id
        gift_with_customer_id = GiftModel.query \
            .filter( or_( GiftModel.method_used_id == id_online, GiftModel.method_used_id == id_credit_card ) ) \
            .filter_by( customer_id=customer_id ) \
            .first()
        return gift_with_customer_id
    except:  # noqa: E722
        raise AdminFindGiftPathError()


def resolve_user( gift_with_customer_id ):
    """If the user is caged or queued then return the model.

    :param gift_with_customer_id: The gift.
    :return: The caged/queued donor models ( at least one will be None ).
    """
    donor_model = None
    try:
        if gift_with_customer_id.user_id == -1:
            caged_donor_model = CagedDonorModel.query.filter_by( gift_id=gift_with_customer_id.id ).one()
            caged_donor_dict = to_json( CagedDonorSchema(), caged_donor_model )
            donor_model = from_json( CagedDonorSchema(), caged_donor_dict.data )
        if gift_with_customer_id.user_id == -2:
            queued_donor_model = QueuedDonorModel.query.filter_by( gift_id=gift_with_customer_id.id ).one()
            queued_donor_dict = to_json( QueuedDonorSchema(), queued_donor_model )
            donor_model = from_json( QueuedDonorSchema(), queued_donor_dict.data )
        return donor_model
    except:  # noqa: E722
        raise BraintreeWebhooksIDPathError( type_id=gift_with_customer_id.customer_id )


def manage_queued_caged_donor( donor_model, gift_id, gift_searchable_id ):
    """Add a row for the donor in either the caged or queued donor table for this transaction.

    :param donor_model: A dictionary with one of the models.
    :param gift_id: The newly created gift ID.
    :param gift_searchable_id: The newly created gift_searchable_id.
    :return:
    """

    try:
        # Make sure we create a new donor and not just update the existing with a new gift_id.
        donor_model.data.gift_id = gift_id
        donor_model.data.gift_searchable_id = gift_searchable_id
        database.session.add( donor_model.data )
    except:  # noqa: E722
        database.session.rollback()
        logging.exception( BraintreeWebhooksCagedDonorPathError().message )


def create_gift_and_transaction(
        gift_with_customer_id,
        webhook_notification,
        recurring_subscription_id,
        agent_id,
        status
):
    """Create the gift and transaction for the new subscription sale.

    :param gift_with_customer_id: The gift with customer ID.
    :param webhook_notification: The Braintree webhook object.
    :param recurring_subscription_id: The subscription ID.
    :param agent_id: The agent ID.
    :param status: The webhook status.
    :return:
    """

    try:
        gift_dict = {
            'user_id': gift_with_customer_id.user_id,
            'customer_id': gift_with_customer_id.customer_id,
            'method_used_id': gift_with_customer_id.method_used_id,
            'sourced_from_agent_id': agent_id,
            'given_to': gift_with_customer_id.given_to,
            'recurring_subscription_id': recurring_subscription_id,
        }

        gift_model = from_json( GiftSchema(), gift_dict )
        database.session.add( gift_model.data )
        database.session.flush()
        gift_id = gift_model.data.id
        gift_searchable_id = gift_model.data.searchable_id

        transaction_id = webhook_notification.subject[ 'subscription' ][ 'transactions' ][ 0 ][ 'id' ]
        amount = webhook_notification.subject[ 'subscription' ][ 'price' ]
        fee = webhook_notification.subject[ 'subscription' ][ 'transactions' ][ 0 ][ 'service_fee_amount' ]
        if not fee:
            fee = '0.00'

        note = 'Recurring subscription fired for customer {}: {}'\
            .format( gift_with_customer_id.customer_id, webhook_notification.kind )

        transaction_dict = {
            'gift_id': gift_id,
            'date_in_utc': datetime.utcnow().strftime( '%Y-%m-%d %H:%M:%S' ),
            'receipt_sent_in_utc': None,
            'enacted_by_agent_id': agent_id,
            'type': 'Gift',
            'status': status,
            'reference_number': transaction_id,
            'gross_gift_amount': Decimal( amount ),
            'fee': fee,
            'notes': note
        }
        transaction_dict.pop( 'id', None )

        transaction_model = TransactionSchema().load( transaction_dict )
        database.session.add( transaction_model.data )
        database.session.flush()
        transaction_dict[ 'id' ] = transaction_model.data.id
        transaction_dict[ 'gift_searchable_id' ] = gift_searchable_id
        return transaction_dict
    except:  # noqa: E722
        database.session.rollback()
        logging.exception( AdminBuildModelsPathError().message )


def get_webhook_status( webhook_notification ):
    """Get the status of the incoming subscription webhook.

    :param webhook_notification: The Braintree webhook notification object.
    :return: status
    """

    status = None
    if webhook_notification.kind == braintree.WebhookNotification.Kind.SubscriptionChargedSuccessfully:
        status = 'Completed'
    elif webhook_notification.kind == braintree.WebhookNotification.Kind.SubscriptionChargedUnsuccessfully:
        status = 'Declined'
    elif webhook_notification.kind == braintree.WebhookNotification.Kind.SubscriptionWentPastDue:
        status = 'Failed'
    elif webhook_notification.kind == braintree.WebhookNotification.Kind.SubscriptionExpired:
        status = 'Failed'
    return status
