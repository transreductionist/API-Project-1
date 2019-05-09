"""SQL queries for the application."""
# pylint: disable=nusa-whitespace-checker


def query_gift_like_uuid( searchable_id_prefix  ):
    """SQL query to find gift by a partial UUID searchable_id: searchable_id_prefix

    :param searchable_id_prefix: Gift partial UUID searchable_id
    :return: SQL query
    """
    return 'SELECT HEX( searchable_id ) FROM {} WHERE HEX( searchable_id ) LIKE "{}%"'\
        .format( 'gift', searchable_id_prefix )


def query_gift_equal_uuid( select_field, searchable_id ):
    """SQL query to find gift by a full UUID searchable_id.

    :param select_field: Field to return in table
    :param searchable_id: Gift UUID searchable_id
    :return: SQL query
    """
    return 'SELECT {} FROM {} WHERE HEX( searchable_id ) = "{}"'\
        .format( select_field, 'gift', searchable_id )


def query_dashboard_transactions( database_name, date0, date1, given_to ):
    """
    Query gifts with transactions between 2 dates and with a specified given_to.
    :return: SQL query
    """

    query = 'SELECT gift.id AS gift_id, gift.given_to AS given_to, transaction.gift_id, transaction.type AS type,\
    transaction.status AS status,\
    transaction.date_in_utc AS date,\
    transaction.gross_gift_amount AS gross_gift_amount\
    FROM\
    {0}.transaction AS transaction\
    LEFT JOIN\
    {0}.gift AS gift ON gift.id = transaction.gift_id\
    WHERE transaction.date_in_utc >= "{1}" AND transaction.date_in_utc < "{2}"\
    AND gift.given_to = "{3}"'.format( database_name, date0, date1, given_to )

    return query


def query_transactions_for_csv():
    """Query all transactions from transaction table (joins with gift and agent table).

    :return: The query to execute.
    """

    query = 'SELECT gift.id AS gift_id, ' \
            'method_used.name, ' \
            'gift.given_to, ' \
            'gift.user_id AS given_by_user_id, ' \
            'agent_sourced.name AS originating_agent_name, ' \
            'agent_sourced.id AS originating_agent_id, ' \
            'HEX(gift.searchable_id) AS searchable_gift_id, ' \
            'txn.gift_id, ' \
            'txn.reference_number, ' \
            'agent_enacted.name AS transaction_agent_name, ' \
            'agent_enacted.id AS transaction_agent_id, ' \
            'txn.type AS transaction_type, ' \
            'txn.status AS transaction_status, ' \
            'txn.date_in_utc AS transaction_date, ' \
            'txn.gross_gift_amount AS transaction_gross,' \
            'txn.fee AS transaction_fee, ' \
            'txn.notes ' \
            'FROM transaction txn ' \
            'LEFT JOIN agent agent_enacted ' \
            'ON agent_enacted.id = txn.enacted_by_agent_id ' \
            'LEFT JOIN gift gift ' \
            'ON gift.id = txn.gift_id ' \
            'LEFT JOIN agent agent_sourced ' \
            'ON agent_sourced.id = gift.sourced_from_agent_id ' \
            'LEFT JOIN method_used ' \
            'ON gift.method_used = method_used.id '

    return query
