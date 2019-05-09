"""Marshmallow schema module for Braintree's sale object. Not part of the application model."""
from decimal import Decimal

from marshmallow import fields
from marshmallow import post_dump
from marshmallow import pre_dump
from marshmallow import Schema

from application.models.agent import AgentModel
# pylint: disable=too-few-public-methods
# pylint: disable=bare-except
# flake8: noqa:E722


class BraintreeSaleSchema( Schema ):
    """Marshmallow schema for two-way serialization of the braintree.Transaction.sale().

    This includes only a small subset of the fields that appear on the braintree.Transaction.sale(). It provides
    a post-dump function for taking contextual data ( gift and transaction dictionaries ) and modifying the key-value
    pairs of the contextual data.
    """

    reference_number = fields.Str( attribute='id' )
    gross_gift_amount = fields.Decimal( attribute='amount' )
    date_in_utc = fields.DateTime( attribute='created_at' )
    payment_instrument_type = fields.Str()
    plan_id = fields.Str()
    fee = fields.Decimal( attribute='service_fee_amount' )
    type = fields.Str()
    status = fields.Str()
    refunded_transaction_id = fields.Str()
    customer_id = fields.Str()

    @pre_dump()
    def initialize_customer_id( self, data ):
        """From the Braintree sale get the customer ID coming into the schema.

        :param data: The Braintree sale data.
        :return:
        """

        self.customer_id = data.customer_details.id

    @post_dump
    def package_gift_and_transaction( self, data ):
        """This function is run after the dump but before return.

        Gives us an opportunity to work withBraintree sale fields before returning to the calling code. A context is
        assigned prior to the dump. This context includes the transaction and gift dictionaries. They are modified
        here using the data.

        :param data: The data passed from the schema to the function.
        :return:
        """

        gift = self.context[ 'gift' ]
        transaction = self.context[ 'transaction' ]

        gift[ 'customer_id' ] = self.customer_id

        transaction[ 'date_in_utc' ] = data[ 'date_in_utc' ]
        transaction[ 'status' ] = 'Completed'

        transaction[ 'gross_gift_amount' ] = data[ 'gross_gift_amount' ]

        if data[ 'refunded_transaction_id' ]:
            transaction[ 'gross_gift_amount' ] = -1 * data[ 'gross_gift_amount' ]
            transaction[ 'type' ] = 'Refund'
        transaction[ 'reference_number' ] = data[ 'reference_number' ]

        is_account_type = data[ 'payment_instrument_type' ] == 'credit_card' \
            or data[ 'payment_instrument_type' ] == 'paypal_account'

        if data[ 'type' ] == 'sale' \
                and is_account_type \
                and not data[ 'status' ] == 'voided' \
                and not data[ 'refunded_transaction_id' ]:
            transaction[ 'type' ] = 'Gift'
        elif data[ 'status' ] == 'voided':
            transaction[ 'type' ] = 'Void'
            transaction[ 'gross_gift_amount' ] = -1 * transaction[ 'gross_gift_amount' ]

        if not data[ 'fee' ]:
            transaction[ 'fee' ] = Decimal( 0.00 )

        sourced_from_agent = AgentModel.get_agent( 'Organization', 'name', 'Braintree' )
        gift[ 'sourced_from_agent_id' ] = sourced_from_agent.id

        data[ 'transaction' ] = transaction
        data[ 'gift' ] = gift
