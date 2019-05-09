"""The unit tests require building several rows in the database at one time, and this provides that functionality."""
import copy
import uuid
from datetime import datetime
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import types

from application.helpers.model_serialization import from_json

SQL_INTEGER = types.Integer
SQL_DECIMAL = types.Numeric
SQL_DATETIME = types.DateTime


def create_model_list( model_schema, model_dict, total_items, iterate_over_key=None ):
    """Builds a list of models. Uses the Marshmallow schema and a dictionary.

    :param model_schema: Marshmallow schema for deserialization.
    :param model_dict: The dictionary to deserialize.
    :param total_items: Total items to build.
    :param iterate_over_key: A key to iterate over.
    :return: List of models.
    """

    # Create a list of models.
    models = []
    i = 1
    while i <= total_items:
        model_copy_dict = copy.deepcopy( model_dict )
        if 'searchable_id' in model_copy_dict:
            model_copy_dict[ 'searchable_id' ] = uuid.uuid4()
        elif 'gift_searchable_id' in model_copy_dict:
            model_copy_dict[ 'gift_searchable_id' ] = uuid.uuid4()
        if iterate_over_key:
            model_copy_dict[ iterate_over_key ] = i
            model = from_json( model_schema, model_copy_dict, create=True )
        else:
            model = from_json( model_schema, model_copy_dict, create=True )
        models.append( model.data )
        i += 1
    return models


def create_gift_transactions_date(
        transaction_schema,
        transaction_dict,
        total_transactions,
        total_gifts ):
    """Builds a list of transactions with iterated gift ID's and dates.

    :param transaction_schema: Marshmallow schema for deseriazation.
    :param transaction_dict: Dictionary to deserialize.
    :param total_transactions: Number of transactions to attach to a gift ID.
    :param total_gifts: Number of gifts to attach transactions to.
    :return: List of transaction models.
    """

    # Create a set of transactions and attach to a specific gift.
    # Here are the time deltas: { gift 1: [ 0, -2, -4, -6 ], gift 2: [ -8, -10, -12, -14 ] }
    date_in_utc = datetime.utcnow().replace( hour=0, minute=0, second=0, microsecond=0 )
    iterate_dict = copy.deepcopy( transaction_dict )
    transaction_models = []
    i = 1
    while i <= total_gifts:
        j = 1
        while j <= total_transactions:
            iterate_dict[ 'gift_id' ] = i
            iterate_dict[ 'date_in_utc' ] = date_in_utc.strftime( '%Y-%m-%d %H:%M:%S' )
            transaction_model = from_json( transaction_schema, iterate_dict, create=True )
            transaction_models.append( transaction_model.data )
            date_in_utc = date_in_utc - timedelta( days=2 )
            j += 1
        i += 1
    return transaction_models


def ensure_query_session_aligned( kwargs ):
    """Loop over dictionary and assert equality."""

    self = kwargs[ 'self' ]
    model_dict = kwargs[ 'model_dict' ]

    fields = [ column.key for column in kwargs[ 'model' ].__table__.columns ]
    for field in fields:
        column = getattr( kwargs[ 'model' ], field, None )
        field_type = column.type

        if field in [ 'id', 'gift_id', 'searchable_id', 'gift_searchable_id', 'campaign_id' ]:
            continue
        elif isinstance( field_type, SQL_INTEGER ):
            field_value = int( model_dict[ field ] )
        elif isinstance( field_type, SQL_DECIMAL ):
            field_value = Decimal( model_dict[ field ] )
        elif isinstance( field_type, SQL_DATETIME ):
            field_value = datetime.strptime( model_dict[ field ], '%Y-%m-%d %H:%M:%S' )
        else:
            field_value = getattr( kwargs[ 'model_data' ], field )

        model_data_attr = getattr( kwargs[ 'model_data' ], field )
        model_query_attr = getattr( kwargs[ 'model_query' ], field )
        model_session_attr = getattr( kwargs[ 'model_session' ], field )
        self.assertEqual( field_value, model_data_attr )
        self.assertEqual( model_data_attr, model_query_attr )
        self.assertEqual( model_query_attr, model_session_attr )
