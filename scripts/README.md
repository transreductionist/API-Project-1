This directory includes any non-web code that may have to be run in support of this application.

# List of Scripts

Run any script using something like

```
python -c "import scripts.manage_sandbox_customers; scripts.manage_sandbox_customers.delete_customer_by_name('Alex', 'Abacrombie')"
```

## crontab

- Every 5 minutes:
    - */5 * * * * python -c "import jobs.braintree;jobs.braintree.manage_status_updates()"
- Every 12 hours:
    - 0 */12 * * * python -c "import jobs.braintree;jobs.braintree.manage_status_updates()"
- The first of every month:
    - 0 0 1 * * python -c "import jobs.full_database_dump;jobs.full_database_dump.get_cron_for_csv()"

## manage_braintree_transactions.py
The following script will aid in the management of Braintree transactions. Currently, there is a function that queries
the database for all transactions, and then ensures that these are in the status of 'settled'. The 'settled' status is
needed for such operations as refunding a transaction. Other functions can be added as needed.

A particularly useful function is called create_database_transactions() and uses online Braintree sales during a
specified date interval to build the initial gift and transaction in the database.

## manage_donate_db.py
The following script will DROP ALL tables and then CREATE ALL. Use with caution! It will remove all existing data, and
then reconstruct the tables with no entries. Other functions can be added to manage other database tasks. To run a
function navigate to the project root and, for example, on the command line type:

## manage_sandbox_customers.py
A module to help with managing Braintree customers. Add functions as required. To run a function on the command line
use something like:
