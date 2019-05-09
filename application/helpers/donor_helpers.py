"""Handles work for the controllers: Build the donors requested from the query parameters."""
from nusa_filter_param_parser.build_query_set import query_set

from application.helpers.manage_paginate import convert_into_page
from application.models.caged_donor import CagedDonorModel
from application.models.queued_donor import QueuedDonorModel


def build_donors_from_query( donor_type, query_terms, page_information, sort_information ):
    """An endpoint that returns gifts filtered by the query terms, paginated, and sorted.

    :param donor_type: Type of donor: caged_donor or queued_donor
    :param query_terms: Query terms for donors
    :param page_information: Paginate information
    :param sort_information: Sort information
    :return: paginated, filtered, sorted donors
    """

    # Build filters for the donors.
    donor_filters = []
    if query_terms:
        for attribute, operator_value in query_terms.items():
            for operator, value in operator_value.items():
                donor_filters.append( ( attribute, operator, value ) )

    if donor_type == 'caged':
        model = CagedDonorModel
        donors_query = CagedDonorModel.query
    else:
        model = QueuedDonorModel
        donors_query = QueuedDonorModel.query

    if donor_filters:
        donors_query = query_set( model, model.query, donor_filters )

    # Handle sorting if requested.
    for sort_by in sort_information:
        if sort_by[ 'value' ] == 'desc':
            donors_query = donors_query.order_by( getattr( model, sort_by[ 'attribute' ] ).desc() )
        else:
            donors_query = donors_query.order_by( getattr( model, sort_by[ 'attribute' ] ).asc() )

    if page_information:
        donors = convert_into_page( donors_query, page_information )
    else:
        donors = donors_query.all()

    return donors
