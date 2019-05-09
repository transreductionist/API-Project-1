The directory contains the application's Cron jobs as well as any queued jobs.

## braintree.py

The module is meant to be used with a scheduler (cron) to manage the updating of transactions in the database based
on changes retrieved from the Braintree API: searches using things like authorized_at, submitted_for_settlement_at,
etc. It uses this data to back-fill the database when possible and also writes data to AWS S3 as CSV files.

- Every 5 minutes:
    - */5 * * * * python -c "import jobs.braintree;jobs.braintree.manage_status_updates()"
- Every 12 hours:
    - 0 */12 * * * python -c "import jobs.braintree;jobs.braintree.manage_status_updates()"

## full_database_dump.py

The module is meant to be used with a scheduler (cron) to manage dumping the complete donation databsae.
This process takes a long time and the decision was to put it in a cron job.
