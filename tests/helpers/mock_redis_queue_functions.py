"""Mock redis queue for functions using it in the code."""
from application.helpers.caging import redis_queue_caging
# pylint: disable=too-few-public-methods


class Job:
    """The func.queue( args ) returns a job object with a method get_id(). This provides that method."""

    def __init__( self, job_id, status ):
        self.job_id = job_id
        self.status = status

    def get_id( self ):
        """The method that the job = func.queue( args ) has for retrieving the job ID.

        :return: Mocked redis queue job ID.
        """
        return self.job_id

    def get_status( self ):
        """The method that the job = func.queue( args ) has for retrieving the job status.

        :return: Mocked redis queue job status.
        """
        return self.status


def mock_caging( user, transaction, environment ):
    """This is the function that mocks the redis_queue_caging.queue() call.

    :param user: The user dictionary
    :param transaction: The transaction dictionary
    :param environment: The environment dictionary
    :return: The job instantiated object with the method get_id().
    """

    redis_queue_caging( user, transaction, environment )
    job = Job( 'redis-queue-job-id', 'queued' )

    return job
