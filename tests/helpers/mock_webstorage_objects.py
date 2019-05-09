"""These are objects to mock some of the WebStorage functions."""
# pylint: disable=too-few-public-methods


def mock_webstorage_init_storage( current_app, bucket=None, path=None ):  # pylint: disable=unused-argument
    """The init_app() function called by the application to set up web storage.

    :param current_app: The current application from Flask.
    :param bucket: An S3 bucket.
    :param path: An S3 bucket path.
    :return:
    """


def mock_webstorage_save( file_name, file_data, metadata=( None, None ) ):  # pylint: disable=unused-argument
    """Save a file to AWS S3.

    We choose to describe the default values for metadata argument as a tuple instead of a dictionary. A
    dictionary allows us to label the keys, e.g. file_source. The issue arises, though, that a dictionary is not
    an immutable type in Python, and so the default may be changed at some later time. This should be avoided.
    Use a tuple, and document the positional arguments, which gives up readability, but protects the
    default value.
        metadata = ( file_source, file_id )

    :param str file_name: The file name.
    :param bin file_data: The binary data.
    :param tuple metadata: Metadata to save with the file.
    :return:
    """


def mock_webstorage_delete( filename ):
    """AWS S3 storage delete method.

    :param filename: File name to delete.
    :return: Boolean
    """

    return filename


def mock_webstorage_s3_file_list():
    """AWS S3 storage API call to get a list of files."""


def mock_webstorage_get_bucket_file( file_name, local_path ):  # pylint: disable=unused-argument
    """AWS S3 storage API call to download a file."""


def mock_generate_presigned_url( bucket, key ):  # pylint: disable=unused-argument
    """Generate a signed URL so client can download file from S3."""

    return 'presigned_url'
