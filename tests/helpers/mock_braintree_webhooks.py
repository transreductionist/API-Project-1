"""These are objects to mock Braintree API calls in the unit tests."""
# pylint: disable=too-few-public-methods
import copy

import mock


class MockObjects:
    """The Braintree objects to be mocked."""

    def __init__( self ):
        pass

    SUBSCRIPTION_WEBHOOK_SUCCESSFUL = mock.Mock(
        kind='subscription_charged_successfully',
        subject={
            'subscription': {
                'id': 'recurring_subscription_id',
                'price': '25.00',
                'transactions': [
                    { 'id': 'braintree_reference_number', 'service_fee_amount': '0.00' },
                    { 'id': 'braintree_reference_number', 'service_fee_amount': '10.00' }
                ]
            }
        }
    )


MockObjects.SUBSCRIPTION_WEBHOOK_UNSUCCESSFUL = copy.copy( MockObjects.SUBSCRIPTION_WEBHOOK_SUCCESSFUL )
MockObjects.SUBSCRIPTION_WEBHOOK_UNSUCCESSFUL.kind = 'subscription_charged_unsuccessfully'

MockObjects.SUBSCRIPTION_WEBHOOK_DUE = copy.copy( MockObjects.SUBSCRIPTION_WEBHOOK_SUCCESSFUL )
MockObjects.SUBSCRIPTION_WEBHOOK_DUE.kind = 'subscription_went_past_due'

MockObjects.SUBSCRIPTION_WEBHOOK_EXPIRED = copy.copy( MockObjects.SUBSCRIPTION_WEBHOOK_SUCCESSFUL )
MockObjects.SUBSCRIPTION_WEBHOOK_EXPIRED.kind = 'subscription_expired'


def mock_subscription_notification( gateway, signature, payload ):  # pylint: disable=unused-argument
    """Notification

    :param gateway:
    :param signature:
    :param payload:
    :return:
    """

    if payload == 'subscription_charged_unsuccessfully':
        return MockObjects.SUBSCRIPTION_WEBHOOK_UNSUCCESSFUL
    if payload == 'subscription_went_past_due':
        return MockObjects.SUBSCRIPTION_WEBHOOK_DUE
    if payload == 'subscription_expired':
        return MockObjects.SUBSCRIPTION_WEBHOOK_EXPIRED
    if payload == 'subscription_charged_successfully':
        return MockObjects.SUBSCRIPTION_WEBHOOK_SUCCESSFUL

    return MockObjects.SUBSCRIPTION_WEBHOOK_SUCCESSFUL
