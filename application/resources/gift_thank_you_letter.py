"""Resource for thank your letter endpoint"""
from flask import current_app
from flask import request
from nusa_filter_param_parser.build_query_set import query_set
from nusa_jwt_auth import get_jwt_claims
from nusa_jwt_auth.restful import AdminResource

from application.controllers.gift_thank_you_letter import get_not_yet_thank_you_gifts
from application.controllers.gift_thank_you_letter import handle_thank_you_letter_logic
from application.exceptions.exception_jwt import JWTRequestError
from application.helpers.email import send_thank_you_letter
from application.models.agent import AgentModel
from application.schemas.gift_thank_you_letter import GiftThankYouLetterSchema
# pylint: disable=no-self-use
# pylint: disable=too-few-public-methods


class GiftsThankYouLetter( AdminResource ):
    """Flask-RESTful resource endpoint for thank you letter."""

    def get( self ):
        """Get all not yet thank you gifts"""

        gifts = get_not_yet_thank_you_gifts()
        result = GiftThankYouLetterSchema( many=True ).dump( gifts )
        return result, 200


class GiftsSendThankYouLetter( AdminResource ):
    """Flask-RESTful resource endpoint to send thank you emails and build a CSV."""

    def post( self ):
        """An endpoint to create thank you letters for a list of email payloads.

        The payload for the GET looks like: [ gift_searchable_id_1, gift_searchable_id_2, gift_searchable_id_3, ... ]
        or possibly an empty list ( [] )
        """

        # Authenticate the admin user.
        data = request.get_json()

        if 'NUSA_DISABLE_JWT_AUTH' in current_app.config and current_app.config[ 'NUSA_DISABLE_JWT_AUTH' ] != '':
            query_terms = [ ( 'name', 'eq', 'Unknown Staff Member' ) ]
        else:
            try:
                ultsys_id = get_jwt_claims()[ 'ultsys_id' ]
                query_terms = [ ( 'user_id', 'eq', ultsys_id ) ]
            except KeyError:
                raise JWTRequestError()

        agent_ultsys = query_set(
            AgentModel,
            AgentModel.query,
            query_terms
        ).one()
        agent_ultsys_id = agent_ultsys.id

        # Handle the logic.
        thank_you_dicts, url = handle_thank_you_letter_logic( data, agent_ultsys_id )

        # Send the list to MassMail endpoint
        send_thank_you_letter( thank_you_dicts )

        return url, 200
