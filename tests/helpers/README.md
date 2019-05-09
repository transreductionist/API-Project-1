This directory contains helper files for common resources and functions for the tests.

# List of Helpers

## braintree_mock_objects.py

These are the mock objects that separate the Donate API code from the Braintree API. For example, there are objects
for Transaction.sale(), Transaction.refund(), and Transaction.void().

## default_dictionaries.py

A collection of dictionary payloads for the unit tests, e.g. payloads to build the models. Call the dictionary and
provide it an argument for key-value pairs to be updated.

## manage_ultsys_user_database.py

The API code incorporates three requests to the current user service. These requests are mocked and requires some data
to work upon, and the database can be used for this purpose. A model and schema are included in the helpers here
and the Donation test database reflects the model.

## mock_ultsys_functions.py

These are the functions and object that allow the Ultsys user endpoints to be mocked. They import the UltsysUserModel
to handle the database.

## mock_ultsys_user_data.py

A list of fake Ultsys user dictionaries that is used to create the MySQL database table.

## model_helpers.py

The unit tests often require building several rows in the database at one time, and this provides that functionality.

## ultsys_user_model.py

The Ultsys user model for the find, update and create mocked endpoints.

## ultsys_user_schema.py

The Ultsys user schema for the find, update and create mocked endpoints.
