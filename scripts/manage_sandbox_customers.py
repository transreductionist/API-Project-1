"""A module to help with managing Braintree customers.

   Add functions as required. To run a function on the command line use something like:

   python -c "import scripts.manage_sandbox_customers;
       scripts.manage_sandbox_customers.delete_customer_by_name( 'Alex', 'Abacrombie' )"
"""
import braintree

from application.app import create_app
from application.helpers.braintree_api import init_braintree_credentials

app = create_app( 'DEV' )  # pylint: disable=C0103

init_braintree_credentials( app )


def delete_customer_by_name( first_name, last_name ):
    """Delete customer from the Vault: must provide full name.

    :param first_name: Customer's first name
    :param last_name: Customer's last name
    :return:
    """

    customers = braintree.Customer.search(
        braintree.CustomerSearch.first_name == first_name,
        braintree.CustomerSearch.last_name == last_name
    )

    for customer in customers.items:
        if customer and customer.first_name == first_name and customer.last_name == last_name:
            print( customer.first_name, customer.last_name, customer.id )
            result = braintree.Customer.delete( customer.id )
            if result.is_success:
                continue
            else:
                print( result.errors )


def list_all_customers():
    """List all the customers in the Sandbox Vault."""

    customers = braintree.Customer.all()
    for customer in customers.items:
        print( customer.first_name, customer.last_name, customer.id )
