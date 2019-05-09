This category strictly contains model mappings to individual data tables, document stores, caches, etc.

Tables are explicitly named. The user table is a stand-in for the final database table to be used for this model.
Notice that the database=SQLAlchemy() is done through the import of flask_essentials. This will keep the Marshmallow
and model SQLAlchemy sessions the same.

# List of Resources

## admin.py

Flask-RESTful resource endpoints for voiding, refunding, reallocating gifts.

## agent.py

Flask-RESTful resource endpoints for the AgentModel.

## app_health.py

Flask-RESTful resource endpoints for getting information about the health of the application.

## braintree_webhooks.py

Flask-RESTful resource endpoints for Braintree webhooks. For example, Braintree has webhooks for Braintree auth,
disbursement, dispute, grant API, sub-merchant account, subscription, and test. Here we implement only the
subscription webhook.

## caged_donor.py

Flask-RESTful resource endpoints for the CagedDonorModel.

## campaign.py

Flask-RESTful resource endpoints for the CampaignModel.

## donate.py

Flask-RESTful resource endpoint to get a Braintree token for payment submission, and creating a sale().

## file_management.py

Flask-RESTful resource endpoints for managing remote files such as AWS S3 resources.

## front_end_caging.py

Flask-RESTful resource endpoints for updating or creating Ultsys users from the front-end.

## gift.py

Flask-RESTful resource endpoints for the GiftModel.

## reprocess_queued_donors.py

Flask-RESTful resource endpoints for reprocessing queued donors.

## transaction.py

Flask-RESTful resource endpoints for the TransactionModel.

## user.py

Flask-RESTful resource endpoints for the Drupal user service.

## utilities.py

Flask-RESTful resource endpoints for various utility endpoints to their associated controllers.
