"""Controllers for Flask-RESTful PaypalETL resources: handle the business logic for the endpoint."""
from application.helpers.paypal_etl import process_paypal_etl
from application.helpers.paypal_etl import validate_file_data_storage
from application.models.agent import AgentModel


def manage_paypal_etl( request ):
    """Handle the logic for PayPal ETL."""

    file_data = request.files.to_dict()

    validated_file_data = validate_file_data_storage( file_data )
    file_storage = validated_file_data[ 'file_storage' ]
    csv_file_as_list = validated_file_data[ 'reader_list' ]

    # The admin_user_id is set to the ultsys id in the JWT validation here.
    # It is used as an agent id when building the models in the called functions.
    # It needs to be converted from the admin_user_id ( ultsys id ) to an agent id.
    admin_user_id = request.form.get( 'admin_user_id' )
    enacted_by_agent = AgentModel.query.filter_by( user_id=admin_user_id ).one_or_none()
    if not enacted_by_agent:
        enacted_by_agent = AgentModel.query.filter_by( name='Unknown Staff Member' ).one()
    enacted_by_agent_id = enacted_by_agent.id

    return process_paypal_etl( enacted_by_agent_id, csv_file_as_list, file_storage )
