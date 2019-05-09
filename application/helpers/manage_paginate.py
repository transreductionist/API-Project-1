"""Module to handle pagination requests."""
from math import ceil

from nusa_filter_param_parser.nusa_filter_param_parser import build_query_string_from_dict
from sqlalchemy import func

from application.exceptions.exception_model import ModelGiftNotFoundError
from application.flask_essentials import database


def build_link_header( page, base_url, query_terms ):
    """Build the previous and next links for the link header.

    :param page: The SQLAlchemy query.
    :param base_url: The URL for the endpoint.
    :param query_terms: The query parser dictionary.
    :return: Links for the link header.
    """

    query_string = ''
    if query_terms:
        query_string = '{}&'.format( build_query_string_from_dict( query_terms ) )

    links = ''
    if page.has_prev:
        links += '<{}?{}rows_per_page={}&page_number={}&page_total={}>; rel="prev"'.format(
            base_url, query_string, page.per_page, page.prev_num, page.total
        )
    if page.has_next:
        if links:
            links += ', '
        links += '<{}?{}rows_per_page={}&page_number={}&page_total={}>; rel="next"'.format(
            base_url, query_string, page.per_page, page.next_num, page.total
        )

    if links == '':
        return None

    return links


def transform_data( base_url, query_terms, page, schema_name ):
    """Transform paginate() dta to return payload.
    :param base_url: Base URL to build the link from.
    :param page: A paginate() object.
    :param page_information: Page number and rows per page.
    :param schema_name: The schema to apply the results to.
    :return: JSON data payload.
    """

    data = {
        'items': schema_name().dump( page.items, many=True ).data
    }

    link_header = build_link_header( page, base_url, query_terms )

    page_data = {
        'page': data,
        'link-header': link_header
    }

    return page_data


def convert_into_page( data, page_information=None ):
    """Take a SQL query and paginate it.
    :param data: A SQLAlchemy query.
    :param page_information: Paginate terms like rows per page and page number.
    :return: A paginate object.
    """

    if page_information:

        per_page = int( page_information[ 'rows_per_page' ][ 'eq' ] )
        page = int( page_information[ 'page_number' ][ 'eq' ] )

        # A quick SQLAlchemy count method.
        total_rows = database.session.execute( data.statement.with_only_columns( [ func.count() ] ) ).scalar()

        total_pages = ceil( total_rows / per_page )
        if total_pages == 0:
            raise ModelGiftNotFoundError
        if page > total_pages:
            page = total_pages

        paginated_page = data.paginate(
            per_page=per_page,
            page=page,
            error_out=True
        )

        return paginated_page

    return data.paginate( per_page=100, page=1, error_out=True )
