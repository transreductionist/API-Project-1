"""A collection of dictionary payloads for the unit tests, e.g. payloads to build the models.

   Call the dictionary and provide it an argument for key-value pairs to be updated. If None is provided
   no key-value pairs are updated and the default dictionary is returned. So, for example, calling the
   get_transaction_dict like:

       get_transaction_dict( { 'transaction': { 'gross_gift_amount': '10.00' } } )

   will return the default dictionary with the gross_gift_amount updated from '1.00' to 10.00'. The update()
   function at the end of the module is called to do the updating.
"""
import collections
import datetime

DATE_IN_UTC = datetime.datetime.utcnow()
DATE_IN_UTC = DATE_IN_UTC.strftime( '%Y-%m-%d %H:%M:%S' )


def get_gift_dict( update_key_values=None ):
    """The GiftModel dictionary for deserialization.

    :param update_key_values: The key-value pairs that should be updated in the default dictionary.
    :return: Updated dictionary
    """

    gift_default = {
        'id': None,
        'searchable_id': None,
        'user_id': None,
        'customer_id': 'customer_id',
        'campaign_id': None,
        'method_used_id': 1,
        'sourced_from_agent_id': 1,
        'given_to': 'ACTION',
        'recurring_subscription_id': None
    }
    return update( update_key_values, gift_default )


def get_transaction_dict( update_key_values=None ):
    """The TransactionModel dictionary for deserialization.

    :param update_key_values: The key-value pairs that should be updated in the default dictionary.
    :return: Updated dictionary
    """

    transaction_default = {
        'id': None,
        'gift_id': None,
        'gift_searchable_id': None,
        'date_in_utc': DATE_IN_UTC,
        'receipt_sent_in_utc': DATE_IN_UTC,
        'enacted_by_agent_id': 1,
        'type': 'Gift',
        'status': 'Completed',
        'reference_number': 'braintree_reference_number',
        'gross_gift_amount': '25.00',
        'fee': '0.00',
        'notes': 'Some text for the transaction.'
    }
    return update( update_key_values, transaction_default )


def get_exists_donor_dict( update_key_values=None ):
    """The UserModel dictionary for deserialization of an existing user/donor.

    :param update_key_values: The key-value pairs that should be updated in the default dictionary.
    :return: Updated dictionary
    """

    exists_donor = {
        'id': None,
        'user_address': {
            'user_email_address': 'joshuaalbers@disney.com',
            'user_first_name': 'Joshua',
            'user_last_name': 'Albers',
            'user_address': '4370 Bombardier Way',
            'user_city': 'Farmington Hills',
            'user_state': 'MI',
            'user_zipcode': '48335',
            'user_phone_number': '7348723251'
        },
        'billing_address': {}
    }
    return update( update_key_values, exists_donor )


def get_new_donor_dict( update_key_values=None ):
    """The CagedDonorModel dictionary for deserialization.

    :param update_key_values: The key-value pairs that should be updated in the default dictionary.
    :return: Updated dictionary
    """

    new_donor = {
        'id': None,
        'user_address': {
            'user_email_address': 'larryalbers@gmail.com',
            'user_first_name': 'Larry',
            'user_last_name': 'Albers',
            'user_address': '1011 Hornblower Drive',
            'user_city': 'Annapolis',
            'user_state': 'MD',
            'user_zipcode': '21401',
            'user_phone_number': '5632028740'
        },
        'billing_address': {}
    }
    return update( update_key_values, new_donor )


def get_caged_donor_dict( update_key_values=None ):
    """The CagedDonorModel dictionary for deserialization.

    :param update_key_values: The key-value pairs that should be updated in the default dictionary.
    :return: Updated dictionary
    """

    caged_donor = {
        'id': None,
        'gift_id': None,
        'gift_searchable_id': None,
        'customer_id': '',
        'campaign_id': None,
        'user_email_address': 'alicealbers@disney.com',
        'user_first_name': 'Alice',
        'user_last_name': 'Albers',
        'user_address': '4370 Bombardier Way',
        'user_city': 'Farmington Hills',
        'user_state': 'MI',
        'user_zipcode': '48335',
        'user_phone_number': '7348723251',
        'times_viewed': 0
    }
    return update( update_key_values, caged_donor )


def get_queued_donor_dict( update_key_values=None ):
    """The QueuedDonorModel dictionary for deserialization.

    :param update_key_values: The key-value pairs that should be updated in the default dictionary.
    :return: Updated dictionary
    """

    queued_donor = {
        'id': None,
        'gift_id': None,
        'gift_searchable_id': None,
        'customer_id': '',
        'campaign_id': None,
        'user_email_address': 'alicealbers@gmail.com',
        'user_first_name': 'Alice',
        'user_last_name': 'Albers',
        'user_address': '4370 Bombardier Way',
        'user_city': 'Farmington Hills',
        'user_state': 'MI',
        'user_zipcode': '48335',
        'user_phone_number': '7348728997',
        'times_viewed': 0
    }
    return update( update_key_values, queued_donor )


def get_agent_dict( update_key_values=None ):
    """The AgentModel dictionary for deserialization.

    :param update_key_values: The key-value pairs that should be updated in the default dictionary.
    :return: Updated dictionary
    """

    agent_default = {
        'id': None,
        'name': 'Braintree',
        'user_id': None,
        'staff_id': None,
        'type': 'Organization'
    }
    return update( update_key_values, agent_default )


def get_agent_jsons():
    """Here is a standard collection of agents used for testing."""

    agent_jsons = [
        { 'name': 'Donate API', 'user_id': None, 'staff_id': None, 'type': 'Automated' },
        { 'name': 'Braintree', 'user_id': None, 'staff_id': None, 'type': 'Organization' },
        { 'name': 'PayPal', 'user_id': None, 'staff_id': None, 'type': 'Organization' },
        { 'name': 'Credit Card Issuer', 'user_id': None, 'staf_id': None, 'type': 'Organization' },
        { 'name': 'Unspecified NumbersUSA Staff', 'user_id': None, 'staff_id': None, 'type': 'Staff Member' },
        { 'name': 'Dan Marsh', 'user_id': 1234, 'staff_id': 4321, 'type': 'Staff Member' },
        { 'name': 'Joshua Turcotte', 'user_id': 7041, 'staff_id': 1407, 'type': 'Staff Member' },
        { 'name': 'Fidelity Bank', 'user_id': None, 'staff_id': None, 'type': 'Organization' }
    ]
    return agent_jsons


def get_donate_dict( update_key_values=None ):
    """The default dictionary for a donation.

    :param update_key_values: The key-value pairs that should be updated in the default dictionary.
    :return: Updated dictionary
    """

    payload_default = {
        'gift': {
            'method_used': 'Web Form Credit Card',
            'given_to': 'NERF',
            'campaign_id': None
        },
        'transaction': {
            'date_of_method_used': '2018-07-12 00:00:00',
            'gross_gift_amount': '10.00',
            'reference_number': '1201',
            'bank_deposit_number': '<bank-deposit-number>',
            'type': 'Gift',
            'notes': 'A note for the transaction.'
        },
        'user': {
            'id': None,
            'user_address': {
                'user_email_address': 'joshuaalbers@disney.com',
                'user_first_name': 'Joshua',
                'user_last_name': 'Albers',
                'user_address': '4370 Bombardier Way',
                'user_city': 'Farmington Hills',
                'user_state': 'MI',
                'user_zipcode': '48335',
                'user_phone_number': '7348723251'
            },
            'billing_address': {
                'billing_email_address': 'joshuaalbers@disney.com',
                'billing_first_name': 'Joshua',
                'billing_last_name': 'Albers',
                'billing_address': '4370 Bombardier Way',
                'billing_city': 'Farmington Hills',
                'billing_state': 'MI',
                'billing_zipcode': '48335',
                'billing_phone_number': '7348723251'
            }
        },
        'payment_method_nonce': 'fake-valid-visa-nonce',
        'recurring_subscription': False,
        'user_id': '3255162'
    }
    return update( update_key_values, payload_default )


def get_campaign_dict( update_key_values=None ):
    """The default dictionary for a campaign.

    :param update_key_values: The key-value pairs that should be updated in the default dictionary.
    :return: Updated dictionary
    """

    campaign = {
        'id': None,
        'name': 'Red, White, and Blue',
        'description': 'A great campaign!',
        'date_from_utc': DATE_IN_UTC,
        'date_to_utc': DATE_IN_UTC,
        'message': 'Message',
        'photo_type': 'png',
        'video_name': 'Gumballs',
        'video_url': 'free_videos.com',
        'background': 1,
        'is_active': 1,
        'is_default': 1
    }
    return update( update_key_values, campaign )


def get_update_campaign_dict( update_key_values=None ):
    """The default dictionary for a campaign.

    :param update_key_values: The key-value pairs that should be updated in the default dictionary.
    :return: Updated dictionary
    """

    campaign_json = {
        'id': None,
        'description': 'A super duper campaign',
        'message': 'Message has been updated',
        'background': '0',
        'photo_type': 'png'
    }
    return update( update_key_values, campaign_json )


def get_campaign_amount_jsons():
    """The default dictionary for building campaign amounts.

    :return: The list of amounts.
    """

    campaign_amount_jsons = [
        { 'amount': '10.00', 'weight': '0', 'campaign_id': '1' },
        { 'amount': '11.00', 'weight': '1', 'campaign_id': '1' },
        { 'amount': '12.00', 'weight': '2', 'campaign_id': '1' },
        { 'amount': '20.00', 'weight': '0', 'campaign_id': '2' },
        { 'amount': '21.00', 'weight': '1', 'campaign_id': '2' },
        { 'amount': '22.00', 'weight': '2', 'campaign_id': '2' },

    ]
    return campaign_amount_jsons


def get_gift_searchable_ids():
    """The default list for building gifts with reproducible UUID's.

    :return: The list of searchable_ids.
    """

    searchable_ids = [
        '9b565221-edd9-4e78-87e8-6841ea7835ed',
        '9b56518a-029a-4d19-bf52-e3eda9b53b39',
        '3bdcd8ee-7250-46b3-a259-7861730f2f5e',
        'd3a6af0d-9589-4ee9-94ca-159def94d22a',
        'b2bac568-50b9-42ee-8c74-42c862e630e1',
        '181ca727-e4a2-434f-ab66-3195c722bfa7'
    ]

    return searchable_ids


def update( update_key_values, base_dictionary ):
    """A routine to update a possibly nested dictionary with key-value pairs.

    :param update_key_values: The key-value pairs to update in the dictionary.
    :param base_dictionary: The dictionary to update.
    :return: Updated base dictionary.
    """

    if update_key_values:
        for base_key, base_value in base_dictionary.items():
            if isinstance( base_value, collections.Mapping ):
                if base_key in update_key_values:
                    base_dictionary[ base_key ] = update(
                        update_key_values.get( base_key, {} ), base_value )
            else:
                if base_key in update_key_values:
                    base_dictionary[ base_key ] = update_key_values[ base_key ]

    return base_dictionary
