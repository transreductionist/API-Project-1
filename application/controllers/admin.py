"""The controllers for administrative endpoints, e.g. correct gifts, reallocate funds, and refund transaction."""
import logging

from flask import current_app

from application.exceptions.exception_critical_path import AdminBuildModelsPathError
from application.exceptions.exception_critical_path import AdminFindGiftPathError
from application.exceptions.exception_critical_path import AdminFindSubscriptionPathError
from application.exceptions.exception_critical_path import AdminTransactionModelPathError
from application.exceptions.exception_critical_path import AdminUpdateSubscriptionPathError
from application.exceptions.exception_critical_path import BuildEmailPayloadPathError
from application.exceptions.exception_critical_path import EmailHTTPStatusError
from application.exceptions.exception_critical_path import EmailSendPathError
from application.exceptions.exception_critical_path import GeneralHelperFindUserPathError
from application.exceptions.exception_critical_path import SendAdminEmailModelError

from application.helpers.admin_correct_gift import correct_transaction
from application.helpers.admin_correct_gift import reallocate_subscription

from application.helpers.admin_record_bounced_check import record_bounced_check
from application.helpers.admin_refund_transaction import refund_transaction
from application.helpers.admin_void_transaction import void_transaction
from application.helpers.braintree_api import get_braintree_transaction
from application.helpers.braintree_api import init_braintree_credentials
from application.helpers.email import send_admin_email
from application.helpers.general_helper_functions import find_user
from application.models.agent import AgentModel
from application.models.gift import GiftModel
from application.models.transaction import TransactionModel


def admin_get_braintree_sale_status( transaction_id ):
    """A function for getting the Braintree status of a sale.

    :param dict transaction_id: The gift searchable ID associated with the Braintree sale.
    :return: Braintree status.
    """

    init_braintree_credentials( current_app )

    try:
        transaction = TransactionModel.query.filter_by( id=transaction_id ).one()
        braintree_id = transaction.reference_number
        braintree_transaction = get_braintree_transaction( braintree_id )
    except AdminTransactionModelPathError as error:
        logging.exception( error.message )
        return False

    return braintree_transaction.status


def admin_record_bounced_check( payload ):
    """A function for recording a bounced check.

    payload = {
        "gift_id": 1,
        "user_id": 1234,
        "reference_number": "201",
        "amount": "10.00",
        "transaction_notes": "Some transaction notes."
    }

    :param dict payload: A dictionary that provides information to record the bounced check.
    :return: Boolean for success or failure.
    """

    try:
        record_bounced_check( payload )
    except AdminTransactionModelPathError as error:
        logging.exception( error.message )
        return False

    return True


def admin_correct_gift( payload ):
    """A function for correcting and or reallocating a gift.

     The reallocation may be to to a different organization, e.g. NERF, ACTION, or SUPPORT.

     The reallocation of a gift will look for a subscription, and if one exists move it to the new plan. It will not
     reconcile any past subscription payments.

     payload = {
          "gift": {
              "gift_searchable_id": "6AE03D8EA2DC48E8874F0A76A1C43D5F",
              "reallocate_to": "NERF"
          },
          "transaction": {
              "reference_number": null,
              "gross_gift_amount": "1000.00",
              "notes": "An online donation to test receipt sent email."
          },
          "user": {
              "user_id": 1
          },
          "agent_ultsys_id": 322156
    }

    :param dict payload: A dictionary that provides information to make the correction and/or reallocation.
    :return: Boolean for success or failure.
    """

    is_a_reallocation = 'reallocate_to' in payload[ 'gift' ] and payload[ 'gift' ][ 'reallocate_to' ]

    # Build the transaction to correct the gift.
    try:
        # Build what we can from the payload and then pass the models on.
        enacted_by_agent_model = AgentModel.get_agent( 'Staff Member', 'user_id', payload[ 'agent_ultsys_id' ] )

        gift_model = GiftModel.query.filter_by( searchable_id=payload[ 'gift' ][ 'searchable_id' ] ).one()

        if is_a_reallocation:
            gift_model.given_to = payload[ 'gift' ][ 'reallocate_to' ]

        transaction_model = TransactionModel(
            gross_gift_amount=payload[ 'transaction' ][ 'corrected_gross_gift_amount' ],
            fee=payload[ 'transaction' ][ 'fee' ],
            notes=payload[ 'transaction' ][ 'notes' ]
        )
        transaction_model, gift_model = correct_transaction( transaction_model, gift_model, enacted_by_agent_model )
    except (
            AdminFindGiftPathError,
            AdminUpdateSubscriptionPathError,
            AdminBuildModelsPathError
    ) as error:
        logging.exception( error.message )
        return False

    import ipdb;ipdb.set_trace()

    # Reallocate the subscription if there is one.
    if gift_model.recurring_subscription_id and is_a_reallocation:
        try:
            braintree_subscription = reallocate_subscription(
                gift_model.recurring_subscription_id, gift_model.given_to
            )
        except (
                AdminFindGiftPathError,
                AdminUpdateSubscriptionPathError,
                AdminBuildModelsPathError
        ) as error:
            logging.exception(error.message)
            return False

    import ipdb;ipdb.set_trace()

    try:
        gift = GiftModel.query.filter_by( searchable_id=payload[ 'gift_searchable_id' ] ).one_or_none()
        user = find_user( gift )
        recurring = False
        if gift.recurring_subscription_id:
            recurring = True
        send_admin_email( transaction, user, recurring )
    except GeneralHelperFindUserPathError as error:
        logging.exception( error.message )
        return False
    except ( SendAdminEmailModelError, EmailSendPathError, BuildEmailPayloadPathError, EmailHTTPStatusError ) as error:
        logging.exception( error.message )
        return False

    return True


def admin_refund_transaction( payload ):
    """A function for refunding a Braintree transaction on a gift.

    payload = {
        "transaction_id": 1,
        "amount": "0.01",
        "user_id": "1234",
        "transaction_notes":
        "Some transaction notes."
    }

    :param dict payload: A dictionary that provides information to make the refund.
    :return: Boolean for success or failure.
    """

    try:
        transaction = refund_transaction( payload )
    except (
            AdminFindGiftPathError,
            AdminFindSubscriptionPathError,
            AdminUpdateSubscriptionPathError,
            AdminBuildModelsPathError
    ) as error:
        logging.exception( error.message )
        return False

    try:
        transaction_model = TransactionModel.query.filter_by( id=transaction[ 'id' ] ).one_or_none()
        gift = GiftModel.query.filter_by( id=transaction_model.gift_id ).one_or_none()
        user = find_user( gift )
        recurring = False
        if gift.recurring_subscription_id:
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


def admin_void_transaction( payload ):
    """A function to void a Braintree transaction on a gift.

    payload = {
        "transaction_id": 1,
        "user_id": "1234",
        "transaction_notes": "Some transaction notes."
    }

    :param dict payload: A dictionary that provides information to void a transaction.
    :return: Boolean for success or failure.
    """

    try:
        transaction = void_transaction( payload )
    except (
            AdminFindGiftPathError,
            AdminFindSubscriptionPathError,
            AdminUpdateSubscriptionPathError,
            AdminBuildModelsPathError
    ) as error:
        logging.exception( error.message )
        return False

    try:
        transaction_model = TransactionModel.query.filter_by( id=transaction[ 'id' ] ).one_or_none()
        gift = GiftModel.query.filter_by( id=transaction_model.gift_id ).one_or_none()
        user = find_user( gift )
        recurring = False
        if gift.recurring_subscription_id:
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
