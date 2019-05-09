This directory contains all the very highest level, most human-readable, code for the entire application.  They
receive the properly deserialized details from the resource, examine them for large decisions, and deploy various
helpers (see ../helpers) to assist in the real heavy lifting.  They then respond to the resource that called them
(see ../resources) with the results.

# List of Controllers

## admin.py

Functionality for reallocating a gift to a different organization: NERF, ACTION, or SUPPORT. Also includes functions
for refunding and voiding a Braintree transaction on a gift

## agent.py

Simple query to return all agents.

## app_health.py

A controller to handle requests about the health of the application.

## braintree_webhooks.py

Braintree has implemented webhooks for Braintree auth, disbursement, dispute, grant API, sub-merchant account,
subscription, and test. In the controller module we include functions for handling these events.

## caged_donor.py

Simple query to return all caged donors.

## campaign.py

Multiple functions to handle the campaign front-end requests, e.g. get_campaigns_by_type() and get_campaigns_by_id().

## donate.py

Handle individual donation by calling Braintree API if 'Online', else build the transaction here. Calls the function
make_braintree_sale( payload ) or make_admin_sale( payload ), both located in helpers, to handle the donation. The first
incorporates the Braintree API to make the sale, the second does not. The Braintree API will create a customer in the
vault if needed, register a subscription, and make the sale. It will return errors if any occur. Both sales call a
caging function to categorize the donor. Once the sale is made gift, transaction, and user dictionaries are returned
and the model updates managed in the present function.

## file_management.py

Controllers for managing remote files such as AWS S3 resources. Currently there is a get file list by bucket and path,
as well as download a file to the users local drive fom a bucket/path and given local_path. Uses query terms to specify
parameters.

## front_end_caging.py

Controllers for updating or creating Ultsys users from the front-end.

## gift.py

Contains a number of controllers for returning Gift objects. There is a simple query to return gifts based on gift ID
or ID's: gift_ids. If a list of ID's is provided those gifts will be returned. If the argument is an integer that
gift will be returned. Finally, if there are no ID's then all gifts are returned. Gives by date or date range will
return the corresponding gifts. There is also a controller for the given_to field, as well as returning all gifts
for a user or list of users.

## reprocess_queued_donors.py

It is possible that a donor gets stuck in the queued donor table. This module allows administrative staff to
reprocess these donors, either en total, or by a list of ID's.

## transaction.py

Simple query to return transactions based on the gift ID or ID's provided. If there is no gift ID all transactions
will be returned. If a gift ID is given all transactions attached to that ID will be returned. Finally, if a list of
gift ID's are provided all transactions attached to those gifts are returned. Transactions by gross gift amount can
be queried. If one amount is provided all transactions with gross gift amounts greater than that are returned. If
a range of amounts is provided all transactions within the range will be returned.
gift ID's are provided all transactions attached to those gifts are returned.

## user.py

The controller handles the payload that will hit one of three endpoints: find, update and create Ultsys user. The
find endpoint takes both search and sort terms and makes a call to Ultsys. The update endpoint also makes a call to
Ultsys and allows updating certain donation fields on the model. The create endpoint hits Drupal.

## utilities.py

The controller handles the utility functions. For example, an administrative user needs the values on a particular
enumerated field of a given model. This module would contain a function to perform that task.
