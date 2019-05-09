"""Module that tests the reallocation of a gift by administrative staff."""
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from statistics import mean

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from application.flask_essentials import database
from application.helpers.sql_queries import query_dashboard_transactions


def dashboard_data( data_type ):
    """A function for reallocating a gift to a different organization: NERF, ACTION, or SUPPORT."""

    if data_type == 'summary':
        data = get_summary_data()
        return data

    return { 'action': None, 'nerf': None, 'support': None }


def get_summary_data():
    """Builds simple summary data."""

    date_start = datetime.utcnow().replace( hour=0, minute=0, second=0, microsecond=0 )
    date_start = date_start + timedelta( days=1 )
    date_times = [
        [ date_start - timedelta( hours=hours ), date_start - timedelta( hours=hours - 1 ) ] for hours in range( 1, 25 )
    ]

    action = build_data_set( date_times, 'ACTION' )
    nerf = build_data_set( date_times, 'NERF' )
    support = build_data_set( date_times, 'SUPPORT' )

    return { 'action': action, 'nerf': nerf, 'support': support }


def build_data_set( date_times, given_to ):
    """Builds some simple statistical measures."""

    donations = []
    max_amounts = []
    min_amounts = []
    mean_amounts = []

    for date_time in date_times:

        try:
            sql_query = query_dashboard_transactions(
                current_app.config[ 'MYSQL_DATABASE' ],
                date_time[ 0 ].strftime( '%Y-%m-%d %H:%M:%S' ),
                date_time[ 1 ].strftime( '%Y-%m-%d %H:%M:%S' ),
                given_to
            )
            results = database.session.execute( sql_query )
            transactions = results.fetchall()
        except SQLAlchemyError as error:
            raise error

        donations.append( len( transactions ) )
        amounts = [ ]

        for transaction in transactions:
            amounts.append( transaction[ 6 ] )

        if amounts:
            max_amounts.append( str( max( amounts ) ) )
            min_amounts.append( str( min( amounts ) ) )
            mean_amounts.append( str( mean( amounts ) ) )
        else:
            max_amounts.append( str( Decimal( ' 0.00' ) ) )
            min_amounts.append( str( Decimal( ' 0.00' ) ) )
            mean_amounts.append( str( Decimal( ' 0.00' ) ) )

    data_set = {
        'donations': donations,
        'max_amounts': max_amounts,
        'min_amounts': min_amounts,
        'mean_amounts': mean_amounts
    }

    return data_set
