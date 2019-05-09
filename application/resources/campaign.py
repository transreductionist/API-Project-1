"""Resource entry point for campaign endpoints."""
from flask import request
from flask_api import status
from flask_restful import Resource
from nusa_jwt_auth.restful import AdminResource

from application.controllers.campaign import build_campaign
from application.controllers.campaign import get_campaign_amounts
from application.controllers.campaign import get_campaign_by_id
from application.controllers.campaign import get_campaigns_by_type
from application.exceptions.exception_campaign import CampaignIsDefaultError
from application.schemas.campaign import CampaignSchema
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use


class CampaignsByActive( Resource ):
    """Flask-RESTful resource endpoints for CampaignModel by ID."""

    def get( self, zero_or_one ):
        """Endpoint to retrieve campaigns by active or inactive."""

        campaigns = get_campaigns_by_type( 'is_active', zero_or_one )
        if campaigns or campaigns == []:
            schema = CampaignSchema( many=True )
            return schema.dump( campaigns ).data

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR


class CampaignsByDefault( Resource ):
    """Flask-RESTful resource endpoints for CampaignModel by ID."""

    def get( self, zero_or_one ):
        """Endpoint to retrieve campaigns by filter criteria."""

        campaigns = get_campaigns_by_type( 'is_default', zero_or_one )
        if campaigns or campaigns == []:
            schema = CampaignSchema( many=True )
            result = schema.dump( campaigns ).data
            if not result:  # pylint: disable=no-else-return
                # Return the empty list.
                return []
            elif len( result ) == 1:
                # If there is one campaign then return the object.
                return result[ 0 ]

            # Handle the case where there are multiple campaigns to return.
            if not zero_or_one:
                # If asking for non-default campaigns return the list.
                return result

            # If asking for default campaign and there is more than one: raise the error.
            raise CampaignIsDefaultError

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR


class GetCampaignById( Resource ):
    """Flask-RESTful resource endpoints for CampaignModel by ID."""

    def get( self, campaign_id ):
        """Endpoint to retrieve campaign its id."""

        campaign = get_campaign_by_id( campaign_id )

        if campaign:
            schema = CampaignSchema()
            result = schema.dump( campaign ).data
            return result, status.HTTP_200_OK
        if not campaign:
            return None, status.HTTP_404_NOT_FOUND

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR


class ManageCampaigns( AdminResource ):
    """Flask-RESTful resource endpoints for CampaignModel by ID."""

    def post( self ):
        """Endpoint to post a campaign."""
        if '_method' in request.form and request.form[ '_method' ] == 'put':
            if build_campaign( request, create=False ):
                return None, status.HTTP_200_OK
        else:
            if build_campaign( request, create=True ):
                return None, status.HTTP_200_OK

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR

    def put( self ):
        """Endpoint to update a campaign."""
        if build_campaign( request, create=False ):
            return None, status.HTTP_200_OK

        return None, status.HTTP_500_INTERNAL_SERVER_ERROR


class AmountsByCampaignId( Resource ):
    """Flask-RESTful resource endpoints for CampaignAmountsModel by campaign ID."""

    def get( self, campaign_id ):
        """Endpoint returns amounts and their weights ( column index ) given a campaign ID."""

        amounts = get_campaign_amounts( campaign_id )
        if amounts:
            return amounts, status.HTTP_200_OK

        return None, status.HTTP_404_NOT_FOUND
