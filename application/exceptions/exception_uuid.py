"""Exception handlers for UUID errors."""
# pylint: disable=too-few-public-methods


class UUIDError( Exception ):
    """Base class for some custom exceptions for UUID errors."""


class UUIDLessThanFiveCharsError( UUIDError ):
    """Exception to handle UUID searches with a prefix less than 5 characters."""

    def __init__( self ):
        super().__init__()
        self.message = 'UUID searchable prefix must be greater than or equal to 5 characters long.'
