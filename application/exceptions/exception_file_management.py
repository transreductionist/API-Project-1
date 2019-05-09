"""Exception handlers for file management."""
# pylint: disable=too-few-public-methods


class FileManagementError( Exception ):
    """Base class for some custom exceptions for the Braintree code."""


class FileManagementIncompleteQueryString( FileManagementError ):
    """Exception to handle Gift model errors."""

    def __init__( self ):
        super().__init__()
        self.message = 'The query string was missing needed parameters.'
