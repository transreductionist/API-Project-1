"""Exception handlers for the PayPal ETL code."""
# pylint: disable=too-few-public-methods


class PayPalETLError( Exception ):
    """Base class for some custom exceptions for the PayPal ETL process."""


class PayPalETLNoFileKeyError( PayPalETLError ):
    """Exception to handle a key error on the file storage object."""

    def __init__( self ):
        super().__init__()
        self.message = 'No file storage key'


class PayPalETLNoFileDataError( PayPalETLError ):
    """Exception to handle empty file storage."""

    def __init__( self ):
        super().__init__()
        self.message = 'No data in the file'


class PayPalETLTooManyRowsError( PayPalETLError ):
    """Exception to handle too many rows in the file."""

    def __init__( self ):
        super().__init__()
        self.message = 'The csv uploaded file is too big. Maximum records/rows is 200,000'


class PayPalETLInvalidColumnsError( PayPalETLError ):
    """Exception to handle invalid columns."""

    def __init__( self ):
        super().__init__()
        self.message = 'The CSV does not have all the default columns'


class PayPalETLFileTypeError( PayPalETLError ):
    """Exception to handle file type error ( should be CSV )."""

    def __init__( self ):
        super().__init__()
        self.message = 'Invalid file format: We only process csv format at the moment.'


class PayPalETLOnCommitError( PayPalETLError ):
    """Exception to handle database commit error."""

    def __init__( self ):
        super().__init__()
        self.message = 'Error on committing to database.'
