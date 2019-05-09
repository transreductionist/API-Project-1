"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
from application.helpers.donor_helpers import build_donors_from_query


def get_donors( donor_type, query_terms, page_information=None, sort_information=None ):
    """An endpoint that returns donors filtered by the query terms, paginated, and sorted.

    The resource separates the query, paginate, and sort terms returned by the request.args parser separately.
    If there are no query terms all donors are returned, otherwise the filtered donors are returned. Pagination and
    sorting are handled if requested.

    Here is an example of query, paginate and sort terms as they might appear in the URL:
        &searchable_id=8C2E84E13E31429F8F311EEFB8CEE621&billing_last_name=Peters&rows_per_page=10&page_number=2.

    :param list donor_type: The type of donor: caged_donor or queued_donor.
    :param list query_terms: A dictionary of query terms.
    :param dict page_information: Paginate terms.
    :param dict sort_information: Sort terms.
    :return: A list of donors.
    """

    donors = build_donors_from_query( donor_type, query_terms, page_information, sort_information )
    return donors
