"""Exception handlers for the Campaigns."""
# pylint: disable=too-few-public-methods


class CampaignError( Exception ):
    """Base class for some custom exceptions for the Campaign code."""


class CampaignIsDefaultError( CampaignError ):
    """Exception to handle Campaign model errors."""

    def __init__( self ):
        super().__init__()
        self.message = 'More than one default campaign was found.'
