"""Exception handlers for the query string deserialization/serialization."""
# pylint: disable=too-few-public-methods


class QueryStringError( Exception ):
    """Base class for some custom exceptions for the filter query string ( deserialize-serialize )."""


class QueryStringImproperError( QueryStringError ):
    """Exception to handle 2-way serialization of query strings."""

    def __init__( self ):
        super().__init__()
        self.message = 'Query string deserialization/serialization error.'
