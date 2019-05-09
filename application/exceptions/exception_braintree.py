"""Exception handlers for the Braintree objects."""
# pylint: disable=too-few-public-methods


class BraintreeError( Exception ):
    """Base class for some custom exceptions for the Braintree code."""


class BraintreeNotInSettlingOrSettledError( BraintreeError ):
    """Exception to handle status checking."""

    def __init__( self ):
        super().__init__()
        self.message = 'Not in Braintree settling or settled status.'


class BraintreeNotInSubmittedForSettlementError( BraintreeError ):
    """Exception to handle status checking."""

    def __init__( self ):
        super().__init__()
        self.message = 'Not in Braintree status submitted for settlement.'


class BraintreeNotIsSuccessError( BraintreeError ):
    """Exception to handle result.is_success errors."""

    def __init__( self, error ):
        super().__init__()
        self.message = error


class BraintreeNotFoundError( BraintreeError ):
    """Exception to handle attempting to refund negative amounts."""

    def __init__( self ):
        super().__init__()
        self.message = 'The Braintree object was not found.'


class BraintreeRefundWithNegativeAmountError( BraintreeError ):
    """Exception to handle attempting to refund negative amounts."""

    def __init__( self ):
        super().__init__()
        self.message = 'Braintree refund attempted resulting in negative balance.'


class BraintreeAttributeError( BraintreeError ):
    """Exception to handle attribute errors while parsing a Braintree error object."""

    def __init__( self ):
        super().__init__()
        self.message = 'Braintree attribute error.'


class BraintreeInvalidSignatureError( BraintreeError ):
    """Exception to handle an invalid signature."""

    def __init__( self ):
        super().__init__()
        self.message = 'Braintree invalid signature.'
