This directory contains the testing suite required to demonstrate that the application is in good working order.

# List of Tests

## test_admin_donate.py

This test suite is designed to verify the administrative donation process for items like checks. One important aspect
of the tests is that they are designed to validate the referential integrity of the models and database when a
donation is created. A donation will create a transaction, gift, and a donor in the database, which refer to one
another. The donor may be a new, or existing donor. They may also be a new, or existing caged donor.

This is a different path from online donations, specifically it does not use the Braintree API, and relies on
other code to manage taking the payload and building the models. It is used for recording checks, and other
similar types of donations.

## test_admin_functions.py

This test suite is designed to verify the administrative functions for refunding and reallocating gifts. One important
aspect of the tests is that they are designed to validate the referential integrity of the models and database when
a donation is updated.

## test_api_endpoints.py

This test suite is designed to verify the basic functionality of the API endpoints. All endpoints that retrieve data
from the database are tested here. These include any calls which are performing queries before returning data. The
following 4 endpoints depend upon the Braintree API and need to be mocked. The first 2 are tested elsewhere, and
mocking the get-token endpoint does not provide a useful test. When appropriate the referential integrity of the
database is tested.

## test_braintree_online_donate.py

This test suite is designed to verify the online donation process. One important aspect of the tests is that they are
designed to validate the referential integrity of the models and database when a donation is created. A donation will
create a transaction, gift, and a donor in the database, which refer to one another. The donor may be a new, or
existing donor. They may also be a new, or existing caged donor.

## test_donate_models.py

This test suite is designed to verify the underlying functions that update the models and categorize a donor. These are
core tests, and validate that, given the correct payload, the database is updated correctly. The functions, e.g.
post_donation, admin_reallocate_gift, and admin_refund_transaction, depend upon the functionality tested here. Other
test suites will handle the mocking of the Braintree API to ensure the referential integrity of the models and
database.
