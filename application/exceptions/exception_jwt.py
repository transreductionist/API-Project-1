"""Exception handlers for JWT errors."""
# pylint: disable=too-few-public-methods


class JWTError( Exception ):
    """Base class for some custom exceptions for UUID errors."""


class JWTRequestError( JWTError ):
    """Exception to handle case where the JWT is not in the request."""

    def __init__( self ):
        super().__init__()
        self.message = 'JWT request error.'
