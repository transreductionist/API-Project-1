"""The main application module with create_app(), resources and error handlers."""
import importlib
import logging
from logging.config import dictConfig
import os

from botocore.exceptions import ClientError as BotoClientError
from flask import Flask
from flask import jsonify
from flask_restful import Api
from marshmallow.exceptions import ValidationError as MarshmallowValidationError
from s3_web_storage.web_storage import WebStorage
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound as SQLAlchemyORMNoResultFoundError

from application.logging_configuration import get_logging_configuration
from application.exceptions.exception_braintree import BraintreeAttributeError
from application.exceptions.exception_braintree import BraintreeInvalidSignatureError
from application.exceptions.exception_braintree import BraintreeNotFoundError
from application.exceptions.exception_braintree import BraintreeNotInSettlingOrSettledError
from application.exceptions.exception_braintree import BraintreeNotInSubmittedForSettlementError
from application.exceptions.exception_braintree import BraintreeNotIsSuccessError
from application.exceptions.exception_braintree import BraintreeRefundWithNegativeAmountError
from application.exceptions.exception_campaign import CampaignIsDefaultError
from application.exceptions.exception_critical_path import AdminBuildModelsPathError
from application.exceptions.exception_critical_path import AdminTransactionModelPathError
from application.exceptions.exception_critical_path import EmailHTTPStatusError
from application.exceptions.exception_file_management import FileManagementIncompleteQueryString
from application.exceptions.exception_jwt import JWTRequestError
from application.exceptions.exception_model import ModelCagedDonorNotFoundError
from application.exceptions.exception_model import ModelCampaignImproperFieldError
from application.exceptions.exception_model import ModelGiftImproperFieldError
from application.exceptions.exception_model import ModelGiftNotFoundError
from application.exceptions.exception_model import ModelTransactionImproperFieldError
from application.exceptions.exception_model import ModelTransactionNotFoundError
from application.exceptions.exception_query_string import QueryStringImproperError
from application.exceptions.exception_ultsys_user import UltsysUserBadRequestError
from application.exceptions.exception_ultsys_user import UltsysUserHTTPStatusCodeError
from application.exceptions.exception_ultsys_user import UltsysUserInternalServerError
from application.exceptions.exception_ultsys_user import UltsysUserMultipleFoundError
from application.exceptions.exception_ultsys_user import UltsysUserNotFoundError
from application.exceptions.exception_uuid import UUIDLessThanFiveCharsError
from application.flask_essentials import database
from application.flask_essentials import jwt
from application.flask_essentials import redis_queue
from application.resources.admin import DonateAdminCorrection
from application.resources.admin import DonateAdminRecordBouncedCheck
from application.resources.admin import DonateAdminRefund
from application.resources.admin import DonateAdminVoid
from application.resources.admin import GetBraintreeSaleStatus
from application.resources.agent import Agents
from application.resources.app_health import Heartbeat
from application.resources.braintree_webhooks import BraintreeWebhookSubscription
from application.resources.campaign import AmountsByCampaignId
from application.resources.campaign import CampaignsByActive
from application.resources.campaign import CampaignsByDefault
from application.resources.campaign import GetCampaignById
from application.resources.campaign import ManageCampaigns
from application.resources.dashboard import DashboardData
from application.resources.donate import DonateGetToken
from application.resources.donate import Donation
from application.resources.donor import Donors
from application.resources.file_management import GetS3File
from application.resources.file_management import GetS3FileList
from application.resources.file_management import GetS3FilePath
from application.resources.front_end_caging import CageDonorAsUltsysUser
from application.resources.front_end_caging import CageDonorUpdate
from application.resources.gift import GiftByUserId
from application.resources.gift import Gifts
from application.resources.gift import GiftsByDate
from application.resources.gift import GiftsByGivenTo
from application.resources.gift import GiftsByPartialSearchableId
from application.resources.gift import GiftUpdateNote
from application.resources.gift_thank_you_letter import GiftsSendThankYouLetter
from application.resources.gift_thank_you_letter import GiftsThankYouLetter
from application.resources.paypal_etl import PaypalETL
from application.resources.reprocess_queued_donors import DonateReprocessQueuedDonors
from application.resources.transaction import TransactionBuild
from application.resources.transaction import TransactionsByGift
from application.resources.transaction import TransactionsByGifts
from application.resources.transaction import TransactionsByGrossGiftAmount
from application.resources.transaction import TransactionsById
from application.resources.transaction import TransactionsByIds
from application.resources.transaction import TransactionsForCSV
from application.resources.user import UltsysUser
from application.resources.utilities import Enumeration
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements


def create_app( app_config_env=None ):
    """Application factory.

    Allows the application to be instantiated with a specific configuration, e.g. configurations for development,
    testing, and production. Implements a configuration loader to augment the Flask app.config() in loading these
    configurations. Supports YAML and tagged environment variables. Manages the application logging level.

    :param str app_config_env: The configuration name to use in loading the configuration variables.
    :return: The Flask application.
    """

    # Set the ENV variable in the Dockerfile. If we can't find a value set the app_config_env to DEFAULT.
    if not app_config_env:
        if 'APP_ENV' in os.environ:
            app_config_env = os.environ[ 'APP_ENV' ]
        else:
            app_config_env = 'DEFAULT'

    # See if the default logging should be set to DEBUG instead of WARNING.
    if 'OVERRIDE_LOGGING' in os.environ:
        override_logging = os.environ[ 'OVERRIDE_LOGGING' ]
    else:
        override_logging = False

    app = Flask( 'donate_api' )

    conf_root = os.path.join( os.path.dirname( __file__ ), '..', 'configuration' )
    importlib.import_module( 'configuration' )
    configuration_module = importlib.import_module( '.config_loader', package='configuration' )
    configuration = configuration_module.ConfigLoader()
    configuration.update_from_yaml_file( os.path.join( conf_root, 'conf.yml' ), app_config_env )
    configuration.update_from_env_variables( app_config_env )

    app.config.update( configuration )
    app.config.update( { 'ENV': app_config_env } )

    wsgi_log_level = 'WARNING'
    gunicorn_log_level = 'WARNING'
    # Set the level of the root logger.
    if 'WSGI_LOG_LEVEL' in app.config and app.config[ 'WSGI_LOG_LEVEL' ] != '':
        wsgi_log_level = app.config[ 'WSGI_LOG_LEVEL' ]
    if 'GUNICORN_LOG_LEVEL' in app.config and app.config[ 'GUNICORN_LOG_LEVEL' ] != '':
        gunicorn_log_level = app.config[ 'GUNICORN_LOG_LEVEL' ]

    # If running gunicorn add gunicorn.error to handlers.
    gunicorn = False
    if __name__ != '__main__':
        gunicorn = True

    dictConfig( get_logging_configuration( wsgi_log_level, gunicorn_log_level, gunicorn ) )
    logging.root.log( logging.root.level, '***** Logging is enabled for this level.' )

    logging.root.log( logging.root.level, '***** app.config[ SQLALCHEMY_DATABASE_URI ]: %s',
                      app.config[ 'SQLALCHEMY_DATABASE_URI' ] )
    logging.root.log( logging.root.level, '***** app.config[ MYSQL_DATABASE ]         : %s',
                      app.config[ 'MYSQL_DATABASE' ] )

    database.init_app( app )

    redis_queue.init_app( app )
    jwt.init_app( app )
    # Absolutely needed for JWT errors to work correctly in production
    app.config.update( PROPAGATE_EXCEPTIONS=True )

    if 'INITIALIZE_WEB_STORAGE' in app.config and app.config[ 'INITIALIZE_WEB_STORAGE' ]:
        WebStorage.init_storage( app, app.config[ 'AWS_DEFAULT_BUCKET' ], app.config[ 'AWS_DEFAULT_PATH' ] )

    api = Api( app )

    api.add_resource( Agents, '/donation/agents' )
    api.add_resource( DashboardData, '/donation/dashboard/<string:data_type>' )
    api.add_resource( DonateGetToken, '/donation/braintree/get-token' )
    api.add_resource( Donors, '/donation/donors/<string:donor_type>' )
    api.add_resource( CageDonorAsUltsysUser, '/donation/cage' )
    api.add_resource( CageDonorUpdate, '/donation/cage/update' )
    api.add_resource( CampaignsByActive, '/donation/campaigns/active/<int:zero_or_one>' )
    api.add_resource( CampaignsByDefault, '/donation/campaigns/default/<int:zero_or_one>' )
    api.add_resource( GetCampaignById, '/donation/campaigns/<int:campaign_id>' )
    api.add_resource( ManageCampaigns, '/donation/campaigns' )
    api.add_resource( AmountsByCampaignId, '/donation/campaigns/<int:campaign_id>/amounts' )
    api.add_resource( Donation, '/donation/donate' )
    api.add_resource( Enumeration, '/donation/enumeration/<string:model>/<string:attribute>' )
    api.add_resource( GiftsByPartialSearchableId, '/donation/gifts/uuid_prefix/<string:searchable_id_prefix>' )
    api.add_resource( GiftByUserId, '/donation/gift/user/<int:user_id>', '/donation/gift/user' )
    api.add_resource( Gifts, '/donation/gifts' )
    api.add_resource( GiftsByDate, '/donation/gifts/date' )
    api.add_resource( GiftsByGivenTo, '/donation/gifts/given-to' )
    api.add_resource( GiftUpdateNote, '/donation/gift/<string:searchable_id>/notes' )
    api.add_resource( GiftsThankYouLetter, '/donation/gifts/not-yet-thanked' )
    api.add_resource( GiftsSendThankYouLetter, '/donation/gifts/send-thank-you-letters' )
    api.add_resource( TransactionsByGift, '/donation/gifts/<string:searchable_id>/transactions' )
    api.add_resource( TransactionBuild, '/donation/gift/transaction' )
    api.add_resource( TransactionsByGifts, '/donation/gifts/transactions' )
    api.add_resource( Heartbeat, '/donation/heartbeat' )
    api.add_resource( DonateAdminCorrection, '/donation/correction' )
    api.add_resource( DonateAdminRecordBouncedCheck, '/donation/record-bounced-check' )
    api.add_resource( DonateAdminRefund, '/donation/refund' )
    api.add_resource( DonateReprocessQueuedDonors, '/donation/reprocess-queued-donors' )
    api.add_resource( GetS3File, '/donation/s3/csv/download' )
    api.add_resource( GetS3FileList, '/donation/s3/csv/files' )
    api.add_resource( GetS3FilePath, '/donation/s3/campaign/<int:campaign_id>/file-path' )
    api.add_resource( GetBraintreeSaleStatus, '/donation/transaction/status/<int:transaction_id>' )
    api.add_resource( TransactionsByIds, '/donation/transactions' )
    api.add_resource( TransactionsById, '/donation/transactions/<int:transaction_id>' )
    api.add_resource( TransactionsByGrossGiftAmount, '/donation/transactions/gross-gift-amount' )
    api.add_resource( TransactionsForCSV, '/donation/transactions/csv' )
    api.add_resource( UltsysUser, '/donation/user' )
    api.add_resource( DonateAdminVoid, '/donation/void' )
    api.add_resource( BraintreeWebhookSubscription, '/donation/webhook/braintree/subscription' )
    api.add_resource( PaypalETL, '/donation/paypal-etl' )

    @app.after_request
    def after_request( response ):  # pylint: disable=unused-variable
        """A handler for defining response headers.

        :param response: an HTTP response object
        :return:
        """

        response.headers.add( 'Access-Control-Allow-Origin', '*' )
        response.headers.add( 'Access-Control-Allow-Headers', 'Content-Type, Authorization' )
        response.headers.add( 'Access-Control-Allow-Methods', 'GET, PUT, POST, DELETE' )
        response.headers.add( 'Access-Control-Expose-Headers', 'Link' )
        return response

    @app.errorhandler( UltsysUserBadRequestError )
    def handle_400( error ):  # pylint: disable=unused-variable
        """HTTP status 400 ( bad request ) error handler.

         :param error: Error message raised by exception.
         :return:
         """

        response = jsonify( handle_error_message( error ) )
        response.status_code = 400
        return response

    @app.errorhandler( BraintreeInvalidSignatureError )
    def handle_401( error ):  # pylint: disable=unused-variable
        """HTTP status 401 ( unauthorized ) error handler.

         :param error: Error message raised by exception.
         :return:
         """
        response = jsonify( handle_error_message( error ) )
        response.status_code = 401
        return response

    @app.errorhandler( AdminTransactionModelPathError )
    @app.errorhandler( BraintreeNotFoundError )
    @app.errorhandler( SQLAlchemyORMNoResultFoundError )
    @app.errorhandler( UltsysUserNotFoundError )
    @app.errorhandler( ModelGiftNotFoundError )
    @app.errorhandler( ModelCagedDonorNotFoundError )
    @app.errorhandler( ModelTransactionNotFoundError )
    @app.errorhandler( AttributeError )
    @app.errorhandler( KeyError )
    def handle_404( error ):  # pylint: disable=unused-variable
        """HTTP status 404 ( not found ) error handler.

        :param error: Error message raised by exception.
        :return:
        """

        response = jsonify( handle_error_message( error ) )
        response.status_code = 404
        return response

    @app.errorhandler( BraintreeNotInSettlingOrSettledError )
    @app.errorhandler( BraintreeNotInSubmittedForSettlementError )
    @app.errorhandler( BraintreeNotIsSuccessError )
    @app.errorhandler( BraintreeRefundWithNegativeAmountError )
    @app.errorhandler( ModelCampaignImproperFieldError )
    @app.errorhandler( ModelGiftImproperFieldError )
    @app.errorhandler( ModelTransactionImproperFieldError )
    @app.errorhandler( FileManagementIncompleteQueryString )
    @app.errorhandler( UUIDLessThanFiveCharsError )
    @app.errorhandler( UltsysUserMultipleFoundError )
    @app.errorhandler( JWTRequestError )
    def handle_422( error ):  # pylint: disable=unused-variable
        """HTTP status 422 ( unprocessable entity ) error handler.

        :param error: Error message raised by exception.
        :return:
        """

        response = jsonify( handle_error_message( error ) )
        response.status_code = 422
        return response

    @app.errorhandler( AdminBuildModelsPathError )
    @app.errorhandler( BraintreeAttributeError )
    @app.errorhandler( MarshmallowValidationError )
    @app.errorhandler( SQLAlchemyError )
    @app.errorhandler( UltsysUserHTTPStatusCodeError )
    @app.errorhandler( UltsysUserInternalServerError )
    @app.errorhandler( ValueError )
    @app.errorhandler( BotoClientError )
    @app.errorhandler( QueryStringImproperError )
    @app.errorhandler( EmailHTTPStatusError )
    @app.errorhandler( CampaignIsDefaultError )
    def handle_500( error ):  # pylint: disable=unused-variable
        """HTTP status 500 ( internal server error ) error handler.

        :param error: Error message raised by exception.
        :return:
        """
        response = jsonify( handle_error_message( error ) )
        response.status_code = 500
        return response

    def handle_error_message( error ):
        """Used by error handlers for handling error and error.message.

        :param error: The error raised by the exception.
        :return: return the error message.
        """

        if hasattr( error, 'message' ):
            logging.exception( error.message )
            return error.message
        if hasattr( error, 'args' ):
            logging.exception( error.args )
            return error.args
        if hasattr( error, 'response' ):
            # This is a BotoCore Client Error ( AWS S3 ).
            logging.exception( error.response[ 'Error' ] )
            return error.response[ 'Error' ]
        logging.exception( error )
        return error

    return app


donation_app = create_app()  # pylint: disable=invalid-name

if __name__ != '__main__':
    gunicorn_logger = logging.getLogger( 'gunicorn.error' )  # pylint: disable=invalid-name
    donation_app.logger.handlers = gunicorn_logger.handlers
    donation_app.logger.setLevel( gunicorn_logger.level )

if __name__ == '__main__':
    donation_app.run( host="127.0.0.1", port=5000, debug=True )
