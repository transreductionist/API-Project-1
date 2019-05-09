"""Controllers for Flask-RESTful resources: handle the business logic for the donation endpoint."""
import logging
from decimal import Decimal

from flask import current_app

from application.exceptions.exception_critical_path import BuildEmailPayloadPathError
from application.exceptions.exception_critical_path import BuildModelsGiftTransactionsPathError
from application.exceptions.exception_critical_path import BuildModelsQueuedDonorPathError
from application.exceptions.exception_critical_path import DonateBuildModelPathError
from application.exceptions.exception_critical_path import EmailHTTPStatusError
from application.exceptions.exception_critical_path import EmailSendPathError
from application.exceptions.exception_critical_path import SendAdminEmailModelError
from application.exceptions.exception_model import ModelGiftImproperFieldError
from application.flask_essentials import database
from application.helpers.admin_sale import make_admin_sale
from application.helpers.braintree_api import generate_braintree_token
from application.helpers.braintree_api import init_braintree_credentials
from application.helpers.braintree_api import make_braintree_sale
from application.helpers.build_models import build_model_queued_donor
from application.helpers.build_models import build_models_sale
from application.helpers.caging import redis_queue_caging
from application.helpers.email import send_admin_email
from application.helpers.general_helper_functions import validate_user_payload
from application.models.gift_thank_you_letter import GiftThankYouLetterModel
# pylint: disable=bare-except
# flake8: noqa:E722


def post_donation( payload ):
    """ Handle individual donation by calling Braintree API if 'Online', else build the transaction here.

    Calls the function make_braintree_sale( payload ) or make_admin_sale( payload ), both located in helpers, to
    handle the donation. The first incorporates the Braintree API to make the sale, the second does not.

    The Braintree API will create a customer in the vault if needed, register a subscription, and make the sale.
    It will return errors if any occur.

    Both sales call a caging function to categorize the donor. Once the sale is made gift, transaction, and user
    dictionaries are returned and the model updates managed in the present function.

    payload = {
        "gift": {
            "method_used": "Web Form Credit Card",
            "date_of_method_used": datetime,
            "given_to": "NERF"
        },
        "transaction": {
            "gross_gift_amount": "10.00",
            "notes": "Some notes for the transaction."
        },
        "user": {
            "user_id": null,
            "user_address": {
              "user_first_name": "Ralph",
              "user_last_name": "Kramden",
              "user_zipcode": "11214",
              "user_address": "328 Chauncey St",
              "user_city": "Bensonhurst",
              "user_state": "NY",
              "user_email_address": "ralph@gothambuscompany.com",
              "user_phone_number": "9172307441"
            },
            "billing_address": {
              "billing_first_name": "Ralph",
              "billing_last_name": "Kramden",
              "billing_zipcode": "11214",
              "billing_address": "7001 18th Ave",
              "billing_city": "Bensonhurst",
              "billing_state": "NY",
              "billing_email_address": "ralph@gothambuscompany.com",
              "billing_phone_number": "9172307441"
            }
        },
        "payment_method_nonce": "fake-valid-visa-nonce",
        "recurring_subscription": false
    }

    If this is an administrative donation then there needs to be 3 additional fields on the payload:

        payload[ 'transaction' ][ 'date_of_method_used' ] = 2018-10-04 00:00:00, e.g. the date on the check.
        payload[ "transaction" ][ "reference_number" ] = "101"
        payload[ "transaction" ][ "bank_deposit_number" ] = "<bank_deposit_number>"

    The agent ID is extracted from the JWT token and placed on the payload if applicable.


    :param dict payload: Dictionary of needed information to make a donation.
    :return: Boolean for success or failure.
    """

    init_braintree_credentials( current_app )

    # This is a fix to a mismatch between what the back-end expects and what the front-end is passing.
    user = payload.pop( 'user' )
    user = validate_user_payload( user )
    payload[ 'user' ] = user

    # If method used is Web Form Credit Card or Admin-Entered Credit Card then make a Braintree sale, otherwise is one
    # of the other administrative requests, e.g. Check, Money Order, Stock, Cash, Other.
    braintree_sale = payload[ 'gift' ][ 'method_used' ].lower() == 'web form credit card' or \
        payload[ 'gift' ][ 'method_used' ].lower() == 'web form paypal' or \
        payload[ 'gift' ][ 'method_used' ].lower() == 'admin-entered credit card'

    # See if we need to make a Braintree sale, that is Online or Credit Card call Braintree API.
    # Since merchant account ID is not set for Support a donation to that cannot be made ( raises an error ).
    # Otherwise make the administrative sale, e.g. check, stock, wire transfer, etc.
    # If the code fails in the conditional the database is not modified and the exception is handled by
    # app.errorhandler().
    if braintree_sale and payload[ 'gift' ][ 'given_to' ].lower() != 'support':
        donation = make_braintree_sale( payload, current_app )
    elif braintree_sale and payload[ 'gift' ][ 'given_to' ].lower() == 'support':
        raise ModelGiftImproperFieldError
    else:
        donation = make_admin_sale( payload )

    # Getting ready to save to the database, and want to prevent orphaned gifts/transactions.
    # The response sent back will have redis job ID, status, and the gift searchable ID.
    response = {}
    try:
        # Call build_models_sale() and if an exception occurs while building gift/transaction roll back and quit.
        # If the gift/transaction is made then see about the Thank You letter and the email. If either fails
        # log and move on.
        build_models_sale( donation[ 'user' ], donation[ 'gift' ], donation[ 'transactions' ] )

        # If the gift amount >= $100 ( current threshold ), add to gift_thank_you_letter table
        if Decimal( donation[ 'transactions' ][ 0 ][ 'gross_gift_amount' ] ) \
                >= Decimal( current_app.config[ 'THANK_YOU_LETTER_THRESHOLD' ] ):
            try:
                database.session.add( GiftThankYouLetterModel( gift_id=donation[ 'transactions' ][ 0 ][ 'gift_id' ] ) )
                database.session.commit()
            except:
                database.session.rollback()
                logging.exception( DonateBuildModelPathError().message )

        try:
            recurring = False
            if 'recurring_subscription_id' in donation[ 'gift' ] and donation[ 'gift' ][ 'recurring_subscription_id' ]:
                recurring = True
            send_admin_email( donation[ 'transactions' ][ 0 ], donation[ 'user' ], recurring )
        except (
                SendAdminEmailModelError,
                EmailSendPathError,
                BuildEmailPayloadPathError,
                EmailHTTPStatusError
        ) as error:
            logging.exception( error.message )

        response[ 'gift_searchable_id' ] = str( donation[ 'user' ][ 'gift_searchable_id' ] )
    except BuildModelsGiftTransactionsPathError as error:
        logging.exception( error.message )

    # Build the queued donor model with whatever information we have from above.
    # It can still help construct what happened if there is an error higher up.
    try:
        build_model_queued_donor( donation[ 'user' ] )
    except BuildModelsQueuedDonorPathError as error:
        logging.exception( error.message )

    # Once on the queue it is out of our hands, but may fail on arguments to queue().
    job = None
    try:
        job = redis_queue_caging.queue(
            donation[ 'user' ], donation[ 'transactions' ], current_app.config[ 'ENV' ]
        )
    except:
        pass

    # If the redis job fails quickly, e.g. the ENV is incorrect, the status will be 'failed'.
    # Otherwise, if it takes more time to fail, the status will be 'queued', 'started', etc.
    # We get what status we can and pass it back.
    response[ 'job_id' ] = None
    response[ 'job_status' ] = None
    if job:
        response[ 'job_id' ] = job.get_id()
        response[ 'job_status' ] = job.get_status()

        logging.debug( 'REDIS CAGING: %s', response )

    return response


def get_braintree_token():
    """Handle token generation for Braintree API.

    The front-end uses hosted fields and requires a Braintree token to make a submission for a sale. On submission
    a payment nonce will be returned to the back-end to create the Transaction.sale( {} ). The initial token is
    created with a call to this endpoint.

    :return: Braintree token.
    """

    init_braintree_credentials( current_app )

    return generate_braintree_token()
