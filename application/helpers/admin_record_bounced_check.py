"""Module to facilitate the recording of a bounced check by administrative staff."""
import datetime
from decimal import Decimal

from application.exceptions.exception_critical_path import AdminFindGiftPathError
from application.exceptions.exception_critical_path import AdminTransactionModelPathError
from application.exceptions.exception_model import ModelGiftImproperFieldError
from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from application.models.agent import AgentModel
from application.models.gift import GiftModel
from application.models.method_used import MethodUsedModel
from application.schemas.transaction import TransactionSchema
# pylint: disable=bare-except
# flake8: noqa:E722


def record_bounced_check( payload ):
    """A function for recording the details of a bounced check.

    The payload required for the bounced check has the following keys:

    payload = {
        "gift_id": 1,
        "user_id": 1234,
        "reference_number": "201",
        "amount": "10.00",
        "transaction_notes": "Some transaction notes."
    }

    The reference number will be most likely the check number.

    :param dict payload: A dictionary that provides information to make the reallocation.
    :return:
    """

    gift_searchable_id = payload[ 'gift_searchable_id' ]
    try:
        gift_model = GiftModel.query.filter_by( searchable_id=gift_searchable_id ).one()

        # The first transaction created has the check amount.
        # The last has the current balance.
        gross_gift_amount = \
            gift_model.transactions[ 0 ].gross_gift_amount - gift_model.transactions[ -1 ].gross_gift_amount
    except:
        raise AdminFindGiftPathError()

    # Make sure the gift exists and that it has method_used='Check'.
    # Do not modify the database if method_used is not cCheck. Handle with app.errorhandler().
    method_used = MethodUsedModel.get_method_used( 'name', 'Check' )
    if gift_model.method_used_id != method_used.id:
        raise ModelGiftImproperFieldError

    enacted_by_agent = AgentModel.get_agent( 'Staff Member', 'user_id', payload[ 'user_id' ] )

    try:
        # If gift exists and method_used is a check, record thet the check bounced.
        date_in_utc = datetime.datetime.utcnow().strftime( '%Y-%m-%d %H:%M:%S' )
        transaction_json = {
            'gift_id': gift_model.id,
            'date_in_utc': date_in_utc,
            'enacted_by_agent_id': enacted_by_agent.id,
            'type': 'Bounced',
            'status': 'Completed',
            'reference_number': payload[ 'reference_number' ],
            'gross_gift_amount': gross_gift_amount,
            'fee': Decimal( 0.00 ),
            'notes': payload[ 'transaction_notes' ]
        }

        transaction = from_json( TransactionSchema(), transaction_json )
        database.session.add( transaction.data )
        database.session.commit()
    except:
        database.session.rollback()
        raise AdminTransactionModelPathError( where='parent' )
