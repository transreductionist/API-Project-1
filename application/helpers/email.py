"""Helper to handle email """
import copy
import datetime
import logging
from decimal import Decimal

import requests
from flask import current_app
from flask_api import status

from application.exceptions.exception_critical_path import BuildEmailPayloadPathError
from application.exceptions.exception_critical_path import EmailHTTPStatusError
from application.exceptions.exception_critical_path import EmailSendPathError
from application.exceptions.exception_critical_path import SendAdminEmailModelError
from application.flask_essentials import database
from application.models.agent import AgentModel
from application.models.gift import GiftModel
from application.models.transaction import TransactionModel

# We want to catch all exceptions and not just one or two.
# pylint: disable=bare-except
# flake8: noqa:E722

MAP_SALE_TYPE = {
    'Other': 'other',
    'Refund': 'REFUND',
    'Subscription': 'recurring',
    'Correction': 'Correction',
    'Void': 'void',
    'Gift': 'onetime'
}


def send_email( data ):
    """The email POST request builder.

    :param data: The email payload.
    :return:
    """

    # pylint: disable=unused-argument
    status_code = None
    try:
        if 'urls' in data:
            log_payload = {
                'payload_type': 'statistics'
            }
        else:
            log_payload = {
                'payload_type': 'donation',
                'id': str( data[ 'gift_id' ] )
            }
        logging.debug( 'EMAIL PAYLOAD: %s', log_payload )

        ultsys_email_api_key = current_app.config[ 'ULTSYS_EMAIL_API_KEY' ]
        ultsys_email_url = current_app.config[ 'ULTSYS_EMAIL_URL' ]
        headers = { 'content-type': 'application/json', 'X-Temporary-Service-Auth': ultsys_email_api_key }

        request = requests.post(
            ultsys_email_url,
            params=data,
            headers=headers
        )
        logging.debug( 'email send url: %s', request.url )
        status_code = request.status_code

        if status_code == status.HTTP_200_OK:
            return True

        # If not caught earlier bubbles up at app.errorhandler()
        if not status_code:
            status_code = 'None'
        raise EmailHTTPStatusError( status_code )

    except EmailHTTPStatusError:
        if not status_code:
            status_code = 'None'
        raise EmailHTTPStatusError( status_code )
    except:  # noqa: E722
        raise EmailSendPathError()


def send_thank_you_letter( thank_you_dicts ):
    """Send thank you letter email.

    We have from the front-end the following data:

        thank_you_dicts = [
            {
                "transaction": {
                    "gift_id": < gift_id >,
                    "date_in_utc": datetime.datetime.utcnow(),
                    "enacted_by_agent_id": < enacted_by_agent_id >,
                    "type": < type >,
                    "status": "Thank You Sent",
                    "reference_number": < reference_number >,
                    "gross_gift_amount": < gross_gift_amount >,
                    "fee": < 0.00 >,
                    "notes": < note >
                }
                "user": {
                    "first_name": < first_name >
                    "last_name": < last_name >,
                    "city": < city >,
                    "state": < state >,
                    "email_address": < email_address >
                }
            }
        ]

     :return:
    """

    for thank_you_dict in thank_you_dicts:
        data = build_email_payload( thank_you_dict[ 'transaction' ], thank_you_dict[ 'user' ] )
        send_email( data )


def send_statistics_report( payload ):
    """Send statistics report

    :param payload: The payload of CSV file URL's on Amazon S3.
    :return:
    """

    email = current_app.config[ 'STATISTICS_GROUP_EMAIL' ]
    data = {
        'email': email,
        'urls': payload
    }
    send_email( data )


def send_admin_email( transaction, user, recurring=False ):
    """The code that sends a receipt for a sale.
    :param transaction: The transaction for the sale.
    :param user: The user on the sale.
    :param recurring: Whether the sale is recurring ( subscription ) or not.
    :return:
    """

    # Make sure if the email has problems and doesn't send the receipt_sent_in_utc is not set.
    email_payload = build_email_payload( transaction, user, recurring )
    logging.info( 'email payload: %s', email_payload )
    send_email( email_payload )

    # Update the transaction with the receipt sent date in UTC.
    try:
        transaction_model = TransactionModel.query.filter_by( id=transaction[ 'id' ] ).one_or_none()
        transaction_model.receipt_sent_in_utc = datetime.datetime.now().strftime( '%Y-%m-%d %H:%M:%S' )
    except:  # noqa: E722
        database.session.rollback()
        raise SendAdminEmailModelError()

    try:
        database.session.commit()
    except:  # noqa: E722
        database.session.rollback()
        raise SendAdminEmailModelError()


def build_transaction( payload_transaction, assign_status ):
    """Build a transaction and attach to the gift for an email sent.

    :param payload_transaction: The transaction from the sale.
    :param assign_status: May be 'Thank You Sent' or 'Receipt Sent'.
    :return: transaction
    """

    enacted_by_agent = AgentModel.get_agent( 'Organization', 'name', 'Donate API' )
    enacted_by_agent_id = str( enacted_by_agent.id )

    transaction = copy.deepcopy( payload_transaction )
    transaction[ 'gift_id' ] = str( payload_transaction[ 'gift_id' ] )
    transaction[ 'gift_searchable_id' ] = str( payload_transaction[ 'gift_searchable_id' ] )
    transaction[ 'date_in_utc' ] = datetime.datetime.utcnow().strftime( '%Y-%m-%d %H:%M:%S' )
    transaction[ 'gross_gift_amount' ] = payload_transaction[ 'gross_gift_amount' ]
    transaction[ 'status' ] = assign_status
    transaction[ 'type' ] = payload_transaction[ 'type' ]
    transaction[ 'enacted_by_agent_id' ] = enacted_by_agent_id
    transaction[ 'notes' ] = 'Receipt sent for {}'.format( transaction[ 'type' ] )

    return transaction


def build_email_payload( transaction, user, recurring=False ):
    """Build the email payload.

    :param transaction: The transaction for the email sent.
    :param user: The user dictionary.
    :param recurring: Whether the sale is recurring ( subscription ) or not..
    :return: email_payload
    """

    try:
        user_payload = user
        if 'user_address' in user:
            user_payload = {
                'first_name': user[ 'user_address' ][ 'user_first_name' ],
                'last_name': user[ 'user_address' ][ 'user_last_name' ],
                'city': user[ 'user_address' ][ 'user_city' ],
                'state': user[ 'user_address' ][ 'user_state' ],
                'email_address': user[ 'user_address' ][ 'user_email_address' ]
            }

        gift = GiftModel.query.filter_by( id=transaction[ 'gift_id' ] ).one()

        # Set the sale type for the Ultsys endpoint: [ refund, recurring, reallocation, void, onetime, other ]
        sale_type = MAP_SALE_TYPE[ 'Other' ]
        if transaction[ 'type' ] in MAP_SALE_TYPE:
            sale_type = MAP_SALE_TYPE[ transaction[ 'type' ] ]

        gross_gift_amount = transaction[ 'gross_gift_amount' ]
        if isinstance( transaction[ 'gross_gift_amount' ], Decimal ):
            gross_gift_amount = str( int( transaction[ 'gross_gift_amount' ] ) )

        gift_transaction = TransactionModel.query.filter_by( gift_id=gift.id, type='Gift' ).one()
        gift_date = gift_transaction.date_in_utc.replace( tzinfo=datetime.timezone.utc ).timestamp()

        email_payload = {
            'gift_date': str( gift_date ),
            'gift_id': str( gift.searchable_id ),
            'firstname': user_payload[ 'first_name' ],
            'lastname': user_payload[ 'last_name' ],
            'amount': gross_gift_amount,
            'city': user_payload[ 'city' ],
            'state': user_payload[ 'state' ],
            'email': user_payload[ 'email_address' ],
            'account': gift.given_to.lower(),
            'type': sale_type,
            'recurring': recurring
        }

        # For refunds get previous gross gift amount before refund ( refund already attached to gift ).
        # There are at least 2 transactions: the refund, and the previous transaction ( maybe type Gift ).
        if transaction[ 'type' ] == 'Refund':
            transactions = TransactionModel.query.filter_by( gift_id=transaction[ 'gift_id' ] ).all()
            email_payload[ 'past_amount' ] = str( transactions[ -2 ].gross_gift_amount )

        return email_payload
    except:  # noqa: E722
        raise BuildEmailPayloadPathError()
