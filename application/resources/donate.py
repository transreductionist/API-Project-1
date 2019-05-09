"""Resources entry point to make a Braintree sale."""
from flask import current_app
from flask import jsonify
from flask import request
from flask_api import status
from flask_restful import Resource
from nusa_filter_param_parser.build_query_set import query_set
from nusa_jwt_auth import get_jwt_claims
from nusa_jwt_auth import jwt_optional

from application.controllers.donate import get_braintree_token
from application.controllers.donate import post_donation
from application.exceptions.exception_critical_path import AdminAgentModelPathError
from application.exceptions.exception_jwt import JWTRequestError
from application.models.agent import AgentModel
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use
# pylint: disable=bare-except
# flake8: noqa:E722


class Donation( Resource ):
    """Flask-RESTful resource endpoint for a Braintree donation transaction."""

    # We need the decorator to place the JWT claims on the stack.
    # This endpoint can be accessed both by an anonymous donor and an administrative staff member.
    @jwt_optional
    def post( self ):
        """Endpoint to post a transaction: online and administrative."""

        payload = request.json
        if payload[ 'gift' ][ 'method_used' ].lower() != 'web form credit card':
            if 'NUSA_DISABLE_JWT_AUTH' in current_app.config and current_app.config[ 'NUSA_DISABLE_JWT_AUTH' ] != '':
                query_terms = [ ( 'name', 'eq', 'Unknown Staff Member' ) ]
            else:
                try:
                    # Set ADMIN to ensure detailed Braintree AVS and CVV logging are enabled.
                    current_app.config[ 'ADMIN' ] = True
                    ultsys_id = get_jwt_claims()[ 'ultsys_id' ]
                    if 'read' not in get_jwt_claims()[ 'roles' ]:
                        query_terms = [ ( 'name', 'eq', 'Unknown Staff Member' ) ]
                    else:
                        query_terms = [ ( 'user_id', 'eq', ultsys_id ) ]
                except KeyError:
                    raise JWTRequestError()
            try:
                agent_ultsys = query_set(
                    AgentModel,
                    AgentModel.query,
                    query_terms
                ).one()
                agent_ultsys_id = agent_ultsys.id
            except:
                raise AdminAgentModelPathError

            payload[ 'sourced_from_agent_user_id' ] = agent_ultsys_id

        response = jsonify( post_donation( payload ) )

        if response:
            response.status_code = status.HTTP_200_OK
            return response

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR


class DonateGetToken( Resource ):
    """Flask-RESTful resource endpoint to get a Braintree token for payment submission."""

    def get( self ):
        """Endpoint to get a Braintree generated token."""

        return get_braintree_token(), status.HTTP_200_OK
