"""Exception handlers for the Ultsys user endpoints."""
# pylint: disable=too-few-public-methods


class UltsysUserError( Exception ):
    """Base class for some custom exceptions for the Braintree code."""


class UltsysUserInternalServerError( UltsysUserError ):
    """Exception to handle Ultsys user query errors."""

    def __init__( self ):
        super().__init__()
        self.message = 'Ultsys user query with internal server error.'


class UltsysUserNotFoundError( UltsysUserError ):
    """Exception to handle Ultsys user query errors."""

    def __init__( self ):
        super().__init__()
        self.message = 'Ultsys user was not found.'


class UltsysUserMultipleFoundError( UltsysUserError ):
    """Exception to handle Ultsys user query errors."""

    def __init__( self ):
        super().__init__()
        self.message = 'Multiple Ultsys users found when expecting only one.'


class UltsysUserBadRequestError( UltsysUserError ):
    """Exception to handle Ultsys user query errors."""

    def __init__( self ):
        super().__init__()
        self.message = 'Ultsys returned a 400.'


class UltsysUserHTTPStatusCodeError( UltsysUserError ):
    """Exception to handle Ultsys user query errors."""

    def __init__( self, message ):
        super().__init__()
        self.message = 'Ultsys error returned un-trapped status: %s' % message
