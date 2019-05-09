"""Exception handlers for the models."""
# pylint: disable=too-few-public-methods


class ModelError( Exception ):
    """Base class for some custom exceptions for the Braintree code."""


class ModelGiftImproperFieldError( ModelError ):
    """Exception to handle Gift model errors."""

    def __init__( self ):
        super().__init__()
        self.message = 'Gift model improper field error.'


class ModelGiftNotFoundError( ModelError ):
    """Exception for a request with no results found."""

    def __init__( self ):
        super().__init__()
        self.message = 'There were no gifts found.'


class ModelTransactionImproperFieldError( ModelError ):
    """Exception to handle Gift model errors."""

    def __init__( self ):
        super().__init__()
        self.message = 'Transaction model improper field error.'


class ModelTransactionNotFoundError( ModelError ):
    """Exception to handle Gift model errors."""
    def __init__( self ):
        super().__init__()
        self.message = 'Transaction model was not found.'


class ModelCampaignImproperFieldError( ModelError ):
    """Exception to handle Gift model errors."""

    def __init__( self ):
        super().__init__()
        self.message = 'Campaign model improper field error.'


class ModelCagedDonorNotFoundError( ModelError ):
    """Exception to handle caged donor not found."""

    def __init__( self ):
        super().__init__()
        self.message = 'The caged donor was not found.'
