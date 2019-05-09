"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
import json
from datetime import datetime

from botocore.exceptions import ClientError as BotoClientError
from flask import current_app
from marshmallow.exceptions import ValidationError as MarshmallowValidationError
from s3_web_storage.web_storage import WebStorage
from sqlalchemy.exc import SQLAlchemyError

from application.exceptions.exception_model import ModelCampaignImproperFieldError
from application.flask_essentials import database
from application.helpers.model_serialization import from_json
from application.models.campaign import CampaignAmountsModel
from application.models.campaign import CampaignModel
from application.schemas.campaign import CampaignAmountsSchema
from application.schemas.campaign import CampaignSchema


def make_campaign( request, create ):
    """A multipart/form-data POST is made from front-end and so build the 2 campaign models.
    The form data looks like:
        form_data = {
            "name": "Red White and Green",
            "description": "A really great campaign",
            "date_from_utc": "2018-04-10 00:00:00",
            "date_to_utc": "2018-04-20 00:00:00",
            "message": "Message",
            "video_name": "Gumballs",
            "video_url": "http://free-videos.com",
            "amounts": '[ { "amount": 10.00 }, { "amount": 20.00 }, { "amount": 30.00 } ]',
            "is_active": "1",
            "is_default": "1",
            "background": "1"
        }

    :param obj request: The request from the front-end with form and file data.
    :param obj create: True for creating a new campaign, False to only update.
    :return: A Boolean where True is successful and False not.
    """

    # Grab the form and file data.
    form_data = request.form.to_dict()
    file_data = request.files.to_dict()

    # Transform form data variables to the correct types.
    validate_form_data( form_data, create )

    # With the correct variable types set, create the new campaign.
    campaign_model = build_campaign_model( form_data, create )

    # Handle the creation of the photo.
    build_campaign_model_file( file_data, campaign_model, create )

    # Finish creating the models by saving the campaign amounts.
    build_campaign_amounts_model( form_data, campaign_model )

    database.session.add( campaign_model.data )
    database.session.commit()

    return True


def validate_form_data( campaign_data, create ):
    """Ensure form data variables are mapped to the correct types, e.g. integers.

    :param dict campaign_data: A dictionary containing the form data from the POST.
    :param bool create: Create or update campaign.
    :return:
    """
    # pylint: disable=too-many-branches

    # 1. If this is an update to an existing campaign that campaign must exist.
    if not create:
        try:
            CampaignModel.query.filter_by( id=int( campaign_data[ 'id' ] ) ).one()
        except SQLAlchemyError as error:
            raise error

    # 2. If there is more than one default campaign the try:except will throw an exception. If the database is
    # empty the default_campaign will be None.
    try:
        default_campaign = CampaignModel.query.filter_by( is_default=1 ).one_or_none()
    except SQLAlchemyError as error:
        raise error

    # Get the default campaign if it exists.
    # default_campaign_id, default_campaign_active, default_campaign_amounts = None, None, None
    # if default_campaign:
    #     default_campaign_active = default_campaign.is_active
    #     default_campaign_amounts = CampaignAmountsModel.query.filter_by( campaign_id=default_campaign.id ).all()

    # For creating or updating campaigns remember that, excluding the ID, there are no required fields on the
    # CampaignModel. The campaign_data may therefore only have campaign_data[ 'id' ] specified on it with other
    # fields on the payload empty strings. For updating a campaign the payload may include a subset of the
    # fields on the model.

    # Make sure supplied campaign data is converted to the correct type.
    # If there are empty strings handle them, e.g. set them to their model defaults or ''
    # If campaign_data[ 'amounts' ] == '[]' then set campaign_data[ 'amounts' ] == []
    # Note that amounts are not on the CampaignModel but in the payload for building CampaignAmountsModel.

    defaults = { 'is_default': 0, 'is_active': 1, 'background': 0 }
    fields = [ column.key for column in CampaignSchema.Meta.model.__table__.columns ]
    fields.append( 'amounts' )
    for field in fields:
        if field not in campaign_data and create:
            if field in [ 'date_from_utc', 'date_to_utc' ]:
                campaign_data[ field ] = datetime.utcfromtimestamp( 0 ).strftime( '%Y-%m-%d %H:%M:%S' )
            else:
                campaign_data[ field ] = None
        elif ( field in campaign_data and not campaign_data[ field ] )\
                and field in [ 'is_default', 'is_active', 'background' ]:
            campaign_data[ field ] = defaults[ field ]
        elif ( field in campaign_data and not campaign_data[ field ] )\
                and field in [ 'date_from_utc', 'date_to_utc' ]:
            campaign_data[ field ] = datetime.utcfromtimestamp( 0 ).strftime( '%Y-%m-%d %H:%M:%S' )
        elif ( field in campaign_data and not campaign_data[ field ] )\
                and field == 'amounts':
            campaign_data[ field ] = None
        elif field in campaign_data and field in [ 'is_default', 'is_active', 'background' ]:
            campaign_data[ field ] = int( campaign_data[ field ] )
        elif field in campaign_data and field == 'amounts':
            campaign_data[ 'amounts' ] = json.loads( campaign_data[ 'amounts' ] )

    # 3. If there are no campaigns in the database then default_campaign.id == None and it must be that we are
    # creating one ( an update would fail above looking up the campaign to update ):
    #    a. campaign_data[ 'create' ] = True
    #    b. campaign_data[ 'is_default' ] = 1
    #    c. campaign_data[ 'amounts' ] must be present and not an empty list
    if create and not default_campaign:
        if campaign_data[ 'is_default' ] == 0 or not campaign_data[ 'amounts' ] or campaign_data[ 'amounts' ] == []:
            raise ModelCampaignImproperFieldError()
        # The default campaign must be active and so force this to 1.
        campaign_data[ 'is_active' ] = 1

    # 4. If creating a campaign and there is at least one already in the database, then if it is to become the default
    # it must have amounts on it. The default must also have the is_active flag set to 1 and we will enforce that
    # here. Toggling of the is_default flag is taken care of elsewhere.
    if create and default_campaign:
        if campaign_data[ 'is_default' ] == 1 \
                and ( not campaign_data[ 'amounts' ] or campaign_data[ 'amounts' ] == [] ):
            raise ModelCampaignImproperFieldError()
        # The default campaign must be active and so force this to 1.
        if campaign_data[ 'is_default' ] == 1:
            campaign_data[ 'is_active' ] = 1

    # 5. If the campaign being updated is the current default campaign there are some restrictions that must be
    # placed on the update. In this case campaign_data[ 'id' ] == default_campaign.id and
    #    a. If campaign_data[ 'is_default' ] = 0 then the campaign cannot be updated
    #    b. If campaign_data[ 'is_default' ] = 1
    #        1. If amounts not present on model then campaign_data[ 'amounts' ] must be present
    #        2. campaign_data[ 'is_active' ] must be 1
    if not create and int( campaign_data[ 'id' ] ) == default_campaign.id:
        # If is_default == None we are not updating the default flag and so don't trap.
        # If is_default == 0 we are updating the default flag and so trap.
        # If is_default == 1 we are not updating the default flag ( already 1 ).
        # Can't allow the following updates to the current default campaign.
        if 'is_default' in campaign_data and campaign_data[ 'is_default' ] == 0:
            raise ModelCampaignImproperFieldError()
        if ( 'is_default' in campaign_data and campaign_data[ 'is_default' ] )\
                and ( not campaign_data[ 'amounts' ] or campaign_data[ 'amounts' ] == [] ):
            raise ModelCampaignImproperFieldError()
        # Make sure is_active is set to 1
        campaign_data[ 'is_active' ] = 1

    # 6. If the campaign being updated is not the current default campaign ensure that campaign_data[ 'is_active' ]
    # is set to 1
    if not create and int( campaign_data[ 'id' ] ) != default_campaign.id:
        if 'is_default' in campaign_data and campaign_data[ 'is_default' ] == 1:
            campaign_data[ 'is_active' ] = 1


def build_campaign_model_file( file_data, campaign_model, create ):
    """Given the campaign model save the photo to S3.

    For creating a campaign the payload either has a photo ( save ) or doesn't ( don't save ). For an update the
    logic is a little bit more involved:

        if campaign_model.data.photo == '' and file_storage.read( 3 ) == b'':
            There is no photo on the model and no photo to save: don't delete && don't save.
        elif campaign_model.data.photo != '' and file_storage.read( 3 ) == b'':
            There is a photo on the model and no photo to save: don't delete && don't save.
        elif file_storage.read( 3 ) != b'':
            if campaign_model.data.photo == '':
                There is no photo on the model and a photo to save: save.
            elif campaign_model.data.photo != '':
                There is a photo on the model and a photo to save: delete && save.

    :param file_data: The file storage object.
    :param campaign_model: The campaign model.
    :param create: Whether to create a new campaign or update an existing one.
    :return:
    """

    # With the campaign ID save the file to AWS and attach photo type to the model.
    # The path to the file is given by the campaign ID and the type. Something like:
    #     image_path = aws_base_url + aws_bucket + '/' aws_path + campaign_id + '.' + file_type
    file_storage_keys = [ file_key for file_key in file_data.keys() ]
    if file_storage_keys:
        file_storage_key = file_storage_keys[ 0 ]
    else:
        return

    file_storage = file_data[ file_storage_key ]
    file_type = file_storage.content_type[ file_storage.content_type.find( '/' ) + 1: ]
    file_name = '{}.{}'.format( campaign_model.data.id, file_type )

    if create:
        if file_storage.read( 3 ) == b'':
            campaign_model.data.photo_type = ''
        else:
            WebStorage.init_storage(
                current_app, current_app.config[ 'AWS_DEFAULT_BUCKET' ], current_app.config[ 'AWS_DEFAULT_PATH' ]
            )
            save_image( file_name, file_storage )
            campaign_model.data.photo_type = file_type
    elif not create:
        if file_storage.read( 3 ) != b'':
            WebStorage.init_storage(
                current_app, current_app.config[ 'AWS_DEFAULT_BUCKET' ], current_app.config[ 'AWS_DEFAULT_PATH' ]
            )
            if campaign_model.data.photo_type != '':
                # Photo on model and photo to save: delete && save.
                file_name_to_delete = '{}.{}'.format( campaign_model.data.id, campaign_model.data.photo_type )
                WebStorage.delete( file_name_to_delete )
            save_image( file_name, file_storage )
            campaign_model.data.photo_type = file_type


def save_image( file_name, file_storage ):
    """Save an image to AWS S3.

    :param file_name: Something like 2.jpeg
    :param file_storage: The file storage object
    :return:
    """

    try:
        file_storage.seek( 0 )
        WebStorage.save( file_name, file_storage.read(), ( 'Campaign', file_name ) )
    except BotoClientError as error:
        raise error


def build_campaign_model( form_data, create ):
    """Save the dictionary to the model.

    :param form_data: What to save to the model
    :param create: Whether a POST or PUT
    :return:
    """

    default_campaigns = []
    if 'is_default' in form_data and form_data[ 'is_default' ]:
        # Get all campaigns where is_default is set.
        default_campaigns = CampaignModel.query.filter_by( is_default=1 ).all()

    # Handle toggling of the field is_default.
    if create and len( default_campaigns ) == 1:
        default_campaigns[ 0 ].is_default = 0
    elif not create and len( default_campaigns ) == 1:
        if default_campaigns[ 0 ].id != form_data[ 'id' ]:
            default_campaigns[ 0 ].is_default = 0

    try:
        if create:
            campaign_model = from_json( CampaignSchema(), form_data )
            database.session.add( campaign_model.data )
            database.session.flush()
        else:
            campaign_model = CampaignModel.query.get( int( form_data[ 'id' ] ) )
            # This is a PUT and the Campaign needs to exist.
            if campaign_model:
                # Make sure the photo_type gets put on the update.
                form_data[ 'photo_type' ] = campaign_model.photo_type
                campaign_model = CampaignSchema().load( form_data, instance=campaign_model, partial=True )
            else:
                raise ModelCampaignImproperFieldError
    except MarshmallowValidationError as error:
        raise error
    except SQLAlchemyError as error:
        database.session.rollback()
        raise error

    return campaign_model


def build_campaign_amounts_model( form_data, campaign_model ):
    """Build the CampaignAmounts model.

    The CampaignAmounts model has an amount and its weight ( column index ).

    :param dict form_data: A dictionary containing the form data from the POST.
    :param campaign_model: The campaign model for its ID.
    :return:
    """

    if 'amounts' in form_data and ( form_data[ 'amounts' ] != '' or form_data[ 'amounts' ] == [] ):
        # Go ahead and update the model.
        try:
            campaign_id = campaign_model.data.id

            # Get all the amounts and weights on the model for the given campaign ID and delete.
            current_amount_models = CampaignAmountsModel.query.filter_by( campaign_id=campaign_id )
            for current_amount_model in current_amount_models.all():
                database.session.delete( current_amount_model )

            # Rebuild amounts.
            campaign_amount_models = []
            for index, amount_weight in enumerate( form_data[ 'amounts' ] ):
                data_dict = { 'amount': amount_weight[ 'amount' ], 'weight': index, 'campaign_id': campaign_id }
                amount_model = from_json( CampaignAmountsSchema(), data_dict )
                campaign_amount_models.append( amount_model.data )
            database.session.bulk_save_objects( campaign_amount_models )
        except MarshmallowValidationError as error:
            raise error
        except SQLAlchemyError as error:
            database.session.rollback()
            raise error
