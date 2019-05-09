"""Module for creating an administrative sale with Braintree."""
import datetime

from application.models.agent import AgentModel
from application.models.method_used import MethodUsedModel
# pylint: disable=bare-except
# flake8: noqa:E722


def make_admin_sale( payload ):
    """Use the payload to build an administrative donation.

    payload = {
      "gift": {
        "method_used": "Check",
        "given_to": "NERF",
      },
      "transaction": {
        "date_of_method_used": "2018-07-12 00:00:00",
        "gross_gift_amount": "15.00",
        "reference_number": "1201",
        "bank_deposit_number": "<bank-deposit-number>",
        "type": "Gift",
        "notes": "A note for the transaction."
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

    Since there is one payload from the front-end, which must include 2 dates and 2 reference numbers, these are
    both included as separate key-value pairs in the payload. This gives us one submit from front to back-end.

    :param dict payload: The payload required to update the models as needed.
    :return dict: Returns transaction and gift dictionaries.
    """

    # We don't want to do caging up front because it takes too long. Move to end of the sale in controller.
    # Assign a category: 'queued' and a user ID of -2 ( -1 is used for caged )
    payload[ 'user' ][ 'category' ] = 'queued'
    payload[ 'gift' ][ 'user_id' ] = -2

    # This is not a Braintree transaction and do set the Braintree customer ID to None.
    payload[ 'user' ][ 'customer_id' ] = ''

    sourced_from_agent = AgentModel.get_agent( 'Staff Member', 'user_id', payload[ 'sourced_from_agent_user_id' ] )
    enacted_by_agent = sourced_from_agent

    method_used = MethodUsedModel.get_method_used( 'name', payload[ 'gift' ][ 'method_used' ] )

    # Create the gift dictionary from admin payload.

    gift = {
        'campaign_id': None,
        'method_used_id': method_used.id if method_used else None,
        'sourced_from_agent_id': sourced_from_agent.id if sourced_from_agent else None,
        'given_to': payload[ 'gift' ][ 'given_to' ].upper(),
        'recurring_subscription_id': None
    }

    # Create the transaction dictionary from the administrative payload.
    # If it is a check or money order add a second transaction to capture the date on the payment.
    transactions = []
    utc_now = datetime.datetime.utcnow()
    transaction_type = payload[ 'transaction' ][ 'type' ]
    transaction_notes = payload[ 'transaction' ][ 'notes' ]
    method_used_date_note = 'Date given is date of method used. {}'.format( transaction_notes )
    fee = 0.00
    if 'fee' in payload and payload[ 'transaction' ][ 'fee' ]:
        fee = payload[ 'transaction' ][ 'fee' ]

    is_check_money_order = payload[ 'gift' ][ 'method_used' ] == 'Check' or\
        payload[ 'gift' ][ 'method_used' ] == 'Money Order'

    transactions.append(
        {
            'date_in_utc': payload[ 'transaction' ][ 'date_of_method_used' ],
            'enacted_by_agent_id': enacted_by_agent.id if enacted_by_agent else None,
            'type': transaction_type,
            'status': 'Completed',
            'reference_number': payload[ 'transaction' ][ 'reference_number' ],
            'gross_gift_amount': payload[ 'transaction' ][ 'gross_gift_amount' ],
            'fee': fee,
            'notes': method_used_date_note if is_check_money_order else transaction_notes
        }
    )

    if is_check_money_order:
        bank_agent = AgentModel.get_agent( 'Organization', 'name', 'Fidelity Bank' )
        bank_agent_id = bank_agent.id

        transactions.append(
            {
                'date_in_utc': utc_now.strftime( '%Y-%m-%d %H:%M:%S' ),
                'enacted_by_agent_id': bank_agent_id,
                'type': 'Deposit to Bank',
                'status': 'Completed',
                'reference_number': payload[ 'transaction' ][ 'bank_deposit_number' ],
                'gross_gift_amount': payload[ 'transaction' ][ 'gross_gift_amount' ],
                'fee': fee,
                'notes': ''
            }
        )

    return { 'transactions': transactions, 'gift': gift, 'user': payload[ 'user' ] }
