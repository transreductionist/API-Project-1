"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
from application.helpers.campaign import make_campaign
from application.models.campaign import CampaignAmountsModel
from application.models.campaign import CampaignModel
from application.schemas.campaign import CampaignAmountsSchema


def get_campaigns_by_type( campaign_type, zero_or_one ):
    """Query the CampaignModel for campaigns with active set.

    :return: All campaigns in active status.
    """
    campaigns = []
    if campaign_type == 'is_active':
        campaigns = CampaignModel.query.filter_by( is_active=zero_or_one ).all()
    elif campaign_type == 'is_default':
        campaigns = CampaignModel.query.filter_by( is_default=zero_or_one ).all()
    return campaigns


def get_campaign_by_id( campaign_id ):
    """Query the CampaignModel for a campaign matching the ID.

    :param dict campaign_id: The Campaign ID.
    :return: The campaign matching ID.
    """

    campaign = CampaignModel.query.filter_by( id=campaign_id ).one_or_none()
    return campaign


def build_campaign( request, create ):
    """With a POST or PUT from campaign front-end build the models.

    :param obj request: The HTTP request.
    :param create: True for creating ( POST ) a new campaign, False to only update ( PUT ).
    :return: Boolean as successful or not.
    """
    if make_campaign( request, create ):
        return True

    return False


def get_campaign_amounts( campaign_id ):
    """Given the campaign ID return its amounts and their weights ( column index ).

    :param int campaign_id: The campaign ID.
    :return: Amounts and their weights associated with the campaign ID.
    """

    # Ensure that the campaign exists otherwise return 404:
    if not CampaignModel.query.filter_by( id=campaign_id ).one_or_none():
        return False

    campaign_amounts = CampaignAmountsModel.query.filter_by( campaign_id=campaign_id ).all()
    amounts = CampaignAmountsSchema( many=True, exclude=[ 'id', 'campaign_id' ] ).dump( campaign_amounts )
    return amounts.data
