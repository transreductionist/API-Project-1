"""Controllers for Flask-RESTful resources: handle the business logic for the Braintree webhooks."""
import logging

import braintree
from flask import current_app

from application.exceptions.exception_braintree import BraintreeInvalidSignatureError
from application.exceptions.exception_critical_path import BraintreeWebhooksIDPathError
from application.exceptions.exception_critical_path import BuildEmailPayloadPathError
from application.exceptions.exception_critical_path import EmailHTTPStatusError
from application.exceptions.exception_critical_path import EmailSendPathError
from application.exceptions.exception_critical_path import GeneralHelperFindUserPathError
from application.exceptions.exception_critical_path import SendAdminEmailModelError
from application.helpers.braintree_api import init_braintree_gateway
from application.helpers.braintree_webhooks import manage_subscription
from application.helpers.email import send_admin_email
from application.helpers.general_helper_functions import find_user
from application.models.gift import GiftModel


def subscription_webhook( form_payload ):
    """Creates the gateway and sends the notification to the helper.

    :param form_payload: Payload from Braintree to our endpoint.
    :return: Boolean
    """

    gateway = init_braintree_gateway( current_app )

    try:
        signature = str( form_payload[ 'bt_signature' ] )
        payload = form_payload[ 'bt_payload' ]
        webhook_notification = get_braintree_notification( gateway, signature, payload )
    except braintree.exceptions.invalid_signature_error.InvalidSignatureError:
        raise BraintreeInvalidSignatureError()

    # In the code below the transaction is retrieved from the manage_subscription method. The transaction returned may
    # be None for several reasons. For example, the Sandbox data has been purged. In this case old subscriptions
    # will still trigger.
    try:
        transaction = manage_subscription( webhook_notification, gateway )
    except BraintreeWebhooksIDPathError as error:
        logging.exception( error.message )
        return False

    if transaction:
        try:
            gift = GiftModel.query.filter_by( id=transaction[ 'gift_id' ] ).one_or_none()
            user = find_user( gift )
            recurring = True
            send_admin_email( transaction, user, recurring )
        except GeneralHelperFindUserPathError as error:
            logging.exception( error.message )
            return False
        except (
                SendAdminEmailModelError,
                EmailSendPathError,
                BuildEmailPayloadPathError,
                EmailHTTPStatusError
        ) as error:
            logging.exception( error.message )
            return False

    return True


def get_braintree_notification( gateway, signature, payload ):
    """A function to return a notification type, e.g. subscriptions or disbursements.

    :param gateway: The Braintree gateway.
    :param signature: The Braintree webhook signature.
    :param payload: The Braintree webhook payload.
    :return: Webhook notification object.
    """

    try:
        return gateway.webhook_notification.parse( signature, payload )
    except braintree.exceptions.invalid_signature_error.InvalidSignatureError:
        raise BraintreeInvalidSignatureError()
