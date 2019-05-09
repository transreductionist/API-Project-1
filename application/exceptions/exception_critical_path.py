"""Exception handlers for the module path errors."""
# pylint: disable=too-few-public-methods


class CriticalPathError( Exception ):
    """Base class for some custom exceptions for handling critical path errors."""

    def __init__( self, errors=None, where=None, type_id=None ):
        super().__init__()
        self.errors = errors
        self.where = where
        self.type_id = type_id


class AdminFindGiftPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: error finding gift.'


class AdminFindSubscriptionPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: error finding subscription.'


class AdminUpdateSubscriptionPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self, errors ):
        super().__init__( errors )
        self.message = '***** Critical path error: ' \
                       'error updating subscription and has the braintree errors %s' % self.errors


class AdminBuildModelsPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: error building models.'


class AdminAgentModelPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: error finding agent.'


class AdminTransactionModelPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self, where ):
        super().__init__( where )
        self.message = '***** Critical path error: finding transaction at %s' % self.where


class BraintreeWebhooksIDPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self, type_id ):
        super().__init__( type_id )
        self.message = '***** Critical path error: {} error finding a braintree sale/customer id %s.' % self.type_id


class BraintreeWebhooksCagedDonorPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: error building caged donor.'


class BraintreeWebhooksGiftThankYouPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: error building gift thank you.'


class BuildModelsGiftTransactionsPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: building gift/transactions error.'


class BuildModelsQueuedDonorPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: building queued donor error.'


class BuildModelsCagedDonorPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: building caged donor error.'


class DonateBuildModelPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: donate build models error.'


class DonateGiftThankYouPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: gift thank you build models error.'


class EmailSendPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: email send.'


class BuildEmailPayloadPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: email payload.'


class EmailHTTPStatusError( CriticalPathError ):
    """Exception to handle HTTP Status codes other than a 200 for email sent POST request."""

    def __init__( self, status_code ):
        super().__init__()
        self.message = '***** Critical path error: HTTP status code error: {}.'.format( status_code )


class SendAdminEmailModelError( CriticalPathError ):
    """Exception to handle HTTP Status codes other than a 200 for email sent POST request."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: building email model error.'


class GeneralHelperFindUserPathError( CriticalPathError ):
    """Exception to handle the email module function path errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: finding user.'


class UpdaterCriticalPathError( CriticalPathError ):
    """Exception to handle Gift model errors."""
    def __init__( self, where, type_id ):
        super().__init__( where, type_id )
        self.message = '***** Critical path error: at {} for sale_id {}.'.format( self.where, self.type_id )


class UltsysUserGetUserPathError( CriticalPathError ):
    """Exception to handle Ultsys user query errors."""

    def __init__( self ):
        super().__init__()
        self.message = '***** Critical path error: get an ultsys user.'
