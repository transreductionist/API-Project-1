"""A Module for general helper functions used across the application."""
import json
import string
from copy import deepcopy

import hvac

from application.exceptions.exception_critical_path import GeneralHelperFindUserPathError
from application.helpers.ultsys_user import get_ultsys_user
from application.models.caged_donor import CagedDonorModel
from application.models.queued_donor import QueuedDonorModel
# pylint: disable=bare-except
# flake8: noqa:E722

HEX_DIGITS_SET = set( string.hexdigits )


def munge_address( street_address ):
    """Take a street address and strip spaces, punctuation, and set all characters to lowercase.

    :param street_address: A street address, or string.
    :return: Munged street address.
    """
    street = ''.join( char for char in street_address.lower() if char not in string.punctuation ).replace( ' ', '' )
    return street


def transform_to_ultsys_query( query_dict ):
    """Function for transforming NUSA query_dict to a Ultsys query_parameters dictionary.

    NUSA apps use a deserializer/serializer to handle query strings. The input to the serializer is request.args,
    which is the query string parsed into an ImmutableMultiDict. The request.args is deserialized into query_dict.
    The query_dict is standardized for NUSA applications, however Ultsys search endpoint expects a slightly different
    set of operators. This function transforms NUSA to Ultsys search dictionaries.

    :param query_dict: A dictionary of query terms from deserialized request.args.
    :return: A dictionary of query parameters that the Ultsys search endpoint expects.
    """

    # The query terms that Ultsys expects are different from what is provided by query_dict.
    # Here we transform the query_dict to what find_ultsys_user needs: search_terms, sort_terms
    search_terms = { }

    # Handle all keys but the sort key if it exists.
    for query_key, query_value in query_dict.items():
        if 'contains' in query_value:
            search_terms[ query_key ] = { 'like': '{}{}{}'.format( '%', query_value[ 'contains' ], '%' ) }
        elif 'le' in query_value:
            search_terms[ query_key ] = { 'lte': query_value[ 'le' ] }
        elif 'ge' in query_value:
            search_terms[ query_key ] = { 'gte': query_value[ 'ge' ] }
        elif query_key != 'sort':
            search_terms[ query_key ] = query_value

    # Handle the sort key if it exists.
    sort_terms = []
    if 'sort' in query_dict:
        sort_terms = [
            { sort_term[ 'attribute' ]: sort_term[ 'value' ] } for sort_term in query_dict[ 'sort' ]
        ]

    query_parameters = {
        'action': 'find',
        'search_terms': search_terms,
        'sort_terms': sort_terms
    }

    return query_parameters


def test_hex_string( string_hex ):
    """Test a hex string for non-hex characters.

    :param string_hex: A hex string
    :return: True if a hex string and False if not
    """

    hex_partial_set = set( string_hex )
    if not HEX_DIGITS_SET.issuperset( hex_partial_set ):
        return False
    return True


def find_user( gift ):
    """Given a gift return the user.

    :param gift: GiftModel with user ID.
    :return: A dictionary with user attributes.
    """

    query = { -1: CagedDonorModel.query, -2: QueuedDonorModel.query }
    try:
        if gift.user_id in [ -1, -2 ]:
            found_donor = query[ gift.user_id ].filter_by( gift_id=gift.id ).one()
            user = {
                'first_name': found_donor.user_first_name,
                'last_name': found_donor.user_last_name,
                'city': found_donor.user_city,
                'state': found_donor.user_state,
                'email_address': found_donor.user_email_address
            }
        else:
            user_query = {
                'ID': { 'eq': gift.user_id }
            }
            ultsys_user_json = get_ultsys_user( user_query )
            found_user = json.loads( ultsys_user_json.content.decode( 'utf-8' ) )[ 0 ]
            user = {
                'first_name': found_user[ 'firstname' ],
                'last_name': found_user[ 'lastname' ],
                'city': found_user[ 'city' ],
                'state': found_user[ 'state' ],
                'email_address': found_user[ 'email' ]
            }
        return user
    except:
        raise GeneralHelperFindUserPathError()


def flatten_user_dict( user ):
    """Given a user with multiple addresses flatten to the account address.

    :param user: A once nested user dictionary, e.g. user[ user_address ] and user[ billing_address ].
    :return: A flattened dictionary with user attributes.
    """

    flattened_user = deepcopy( user )
    for user_key in user.keys():
        if isinstance( user[ user_key ], dict ):
            del flattened_user[ user_key ]
            for flattened_key, flattened_value in user[ user_key ].items():
                flattened_user[ flattened_key ] = flattened_value

    return flattened_user


def validate_user_payload( user ):
    """This is a fix to a mismatch between what the back-end expects and what the front-end is passing.

    :param user: The user payload from the front-end.
    :return: The validated payload for the user.
    """

    # If user contains a dictionary with key 'user_address' then it is not caged or queued.
    # Make sure it has the correct keys. The user dictionary may have other key-value pairs in it,
    # e.g searchable_id, and these need to be kept.
    if isinstance( user[ 'user_address' ], dict ):
        user_address_tmp = user.pop( 'user_address', None )
        billing_address_tmp = user.pop( 'billing_address', None )

        user_address = {}
        for user_key, user_value in user_address_tmp.items():
            if 'user_' not in user_key:
                user_key = 'user_{}'.format( user_key )
            user_address[ user_key ] = user_value

        billing_address = {}
        if billing_address_tmp:
            for billing_key, billing_value in billing_address_tmp.items():
                if 'billing_' not in billing_key:
                    billing_key = 'billing_{}'.format( billing_key )
                billing_address[ billing_key ] = billing_value

        user[ 'user_address' ] = user_address
        user[ 'billing_address' ] = billing_address
    elif isinstance( user[ 'user_address' ], str ):
        user_keys = [
            'user_first_name',
            'user_last_name',
            'user_zipcode',
            'user_address',
            'user_city',
            'user_state',
            'user_email_address',
            'user_phone_number'
        ]
        user_address = {}
        for user_key in user_keys:
            user_address[ user_key ] = user.pop( user_key, None )
        user[ 'user_address' ] = user_address
        user[ 'billing_address' ] = {}

    return user


def get_date_with_day_suffix( python_datetime ):
    """Converts a datetime into a format such as: October 21st, 2018.

    :param python_datetime:
    :return: The formatted date.
    """

    date = python_datetime.strftime( '%Y,%B,%d' ).split( ',' )
    day = date[ 2 ]
    if day in [ '01', '21', '31' ]:
        day_str = '{}{}'.format( day, 'st' )
    elif day in [ '02', '22' ]:
        day_str = '{}{}'.format( day, 'nd' )
    elif day in [ '03', '23' ]:
        day_str = '{}{}'.format( day, 'rd' )
    else:
        day_str = '{}{}'.format( day, 'th' )

    # This is going into a CSV and so use double quotes to contain the comma.
    date_str = '{}{} {}, {}{}'.format( '\"', date[ 1 ], day_str, date[ 0 ], '\"' )

    return date_str


def get_vault_data( url, vault_token, secret ):
    """Get vault data.

    :param url: Something like: 'https://vault.numbersusa.net:8200'.
    :param vault_token: The vault token for the secret.
    :param secret: Such as 'secret/database/dbreplica-datastudy'
    :return:
    """

    client = hvac.Client(
        url=url,
        token=vault_token
    )
    vault = client.read( secret )

    return vault
