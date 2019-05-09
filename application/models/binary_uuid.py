"""TypeDecorator allows custom types which add bind-parameter/result-processing behavior to an existing type object"""
# pylint: disable=R0903
import uuid

from sqlalchemy.dialects.mysql import BINARY
from sqlalchemy.types import TypeDecorator


class BinaryUUID( TypeDecorator ):
    """Optimize UUID keys. Store as 16 bit binary, retrieve as uuid."""

    # Required and identifies the TypeEngine class.
    impl = BINARY( 16 )

    def process_bind_param( self, value, dialect ):  # pylint: disable=no-self-use, unused-argument
        """On the way in.

        :param value: UUID
        :param dialect:
        :return:
        """

        try:
            return value.bytes
        except AttributeError:
            try:
                return uuid.UUID( value ).bytes
            except TypeError:
                return value

    def process_result_value( self, value, dialect ):  # pylint: disable=no-self-use, unused-argument
        """On the way out.

        :param value: UUID in bytes
        :param dialect:
        :return:
        """

        return uuid.UUID( bytes=value )
