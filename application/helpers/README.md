This directory contains significantly lower level, heavy duty, code mean to provide various controllers with highly
abstracted and readable logic.  It is anticipated that any one helper may be utilized by any number of controllers.
Even so, helper functions should be distributed to various helper .py files categorically, to ease in understanding
the application at a glance.

# List of Helpers

## admin_reallocate_gift.py
A function for reallocating a gift to a different organization: NERF, ACTION, or SUPPORT. If the donation needs to be
reallocated then the gross gift amount, which is adjusted for refunds and other like transactions, should be moved to
the specified organization. The subscription should be modified to the correct plan, and this is accomplished by
retrieving the default payment method token.

## admin_record_bounced_check.py

An administrative function for recording the details of a bounced check, building a gift and transaction for the
check.

## admin_refund_transaction.py

A function for refunding a Braintree transaction on a gift. Find the transaction in the database and get the Braintree
transaction number. Configure the Braintree API and make the refund through Braintree. For a transaction to be
refunded it must be in the Braintree status Settling, or Settled.

## admin_sale.py

Use the payload to build an administrative donation.

## admin_void_transaction.py

A function for voiding a Braintree transaction on a gift. Find the transaction in the database and get the Braintree
transaction number. Configure the Braintree API and void the transaction. For a transaction to be voided it must be
in the Braintree status Submitted for Settlement.

## braintree_api.py

This module provides functionality for interacting with the Braintree API. It creates sales, subscriptions, refunds,
and voids transactions, among other things. A list of some of the functions:

- make_braintree_refund(braintree_id, amount)
- make_braintree_void(braintree_id)
- make_braintree_sale(payload)
- get_braintree_customer(user)
- create_braintree_customer(user)
- validate_braintree_customer(customer_id)
- is_customer_update_required(user, customer)
- update_braintree_customer(update_dict, customer_id)
- create_braintree_sale(payment_method_nonce, gross_gift_amount, customer_id)
- create_braintree_subscription(payment_method_token, plan_id, gross_gift_amount)
- create_braintree_payment_method(customer_id, payment_method_nonce)
- create_braintree_refund(transaction_id, amount)
- configure_braintree()
- generate_braintree_token()
- handle_braintree_errors(result, braintree_type)

The function make_ braintree_sale(payload) deserves a comment about how the payment method nonce is used. The payment
method nonce is a one time use nonce, and so needs to be used properly within the process flow for creating a sale.
Sometimes we need to create a Braintree customer and a sale. Both take require a payment method nonce. If a Braintree
subscription is requested that needs, what is called a payment method token instead. So, there are considerations
to make when creating a Braintree sale.

## braintree_webhooks.py

A function for handling Braintree webhooks. Currently it manages subscription webhooks, and the URL set on the
sandbox is:
- http://205.175.220.10:7777/donation/webhook/braintree/subscription

Braintree also has Dispute and Disbursement webhooks.

## build_models.py

Given the dictionaries for the models go ahead and build them.

## build_output_file.py

A module that provides functions to build output files as BytesIO stream and then save it to persistent storage.

## caging.py

Given a dictionary for the UserModel function categorizes a donor into: exists, caged, cage, or new. More details
may be found in the doc string, or online on the Wiki.

## campaign.py

A module that manages the tasks associated with the campaigns UI. For example, it builds the models, and
saves/deletes images to AWS S3.

## front_end_caging.py

Helper file to handle the logic for front-end caging. This includes creating and updating Ultsys users, as well as
making modifications to the database.

## general_helper_functions.py

This module contains general helper functions that are useful across the application.

## manage_models.py

A module that manages the models, e.g. create a new transaction attached to a specified gift.

## manage_paginate.py

A module that manages the pagination of model requests. This code is largely taken from RECIPSapi, and adds
link header functionality.

## model_serialization.py

Takes the model_dictionary and deserializes it into the model using its Marshmallow schema: model_schema. SQLAlchemy
db.session.add() creates a new object if an ID is not provided, and updates an object if an ID is provided. Which
from the fields of the Model. If create is False, the model will be updated, and the dictionary must have the ID.

## ultsys_user.py

This is a helper module that is the low level code for handling the request to find, update, or create an users. The
find and update functionality interfaces with Ultsys, while the create makes a call to Drupal.
