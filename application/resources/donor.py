"""Resources entry point for caged donor endpoints."""
# pylint: disable=too-few-public-methods
# pylint: disable=no-self-use
from flask import jsonify
from flask import request
from nusa_filter_param_parser.nusa_filter_param_parser import build_filter_from_request_args
from nusa_jwt_auth.restful import AdminResource

from application.controllers.donor import get_donors
from application.helpers.general_helper_functions import test_hex_string
from application.helpers.manage_paginate import transform_data
from application.schemas.caged_donor import CagedDonorSchema
from application.schemas.queued_donor import QueuedDonorSchema


class Donors( AdminResource ):
    """Flask-RESTful resource endpoints for the CagedDonorModel and the QueuedDonorModel."""

    def get( self, donor_type ):
        """Simple endpoint to retrieve rows from table given a set of query terms and paginate if requested.

        :param donor_type: Either caged or queued.
        :return: donors
        """

        # Grab the donor type and make sure it is one of the allowed values.
        if donor_type not in [ 'caged', 'queued' ]:
            raise TypeError

        query_terms = build_filter_from_request_args( request.args )

        # Sanitize incoming partial UUID to only hex characters.
        if 'searchable_id' in query_terms:
            if 'eq' in query_terms[ 'searchable_id' ]:
                is_hex_string( query_terms[ 'searchable_id' ][ 'eq' ] )
            elif 'in' in query_terms[ 'searchable_id' ] or 'nin' in query_terms[ 'searchable_id' ]:
                for in_nin in query_terms[ 'searchable_id' ]:
                    for searchable_id in query_terms[ 'searchable_id' ][ in_nin ]:
                        is_hex_string( searchable_id )

        page_information = {}
        sort_information = []
        if query_terms:
            page_information = {}
            if 'paginate' in query_terms and query_terms[ 'paginate' ]:
                page_information = {
                    'page_number': query_terms[ 'paginate' ][ 'page_number' ],
                    'rows_per_page': query_terms[ 'paginate' ][ 'rows_per_page' ]
                }
                del query_terms[ 'paginate' ]

            if 'sort' in query_terms and query_terms[ 'sort' ]:
                sort_information = query_terms[ 'sort' ]
                del query_terms[ 'sort' ]

        donors = get_donors(
            donor_type,
            query_terms,
            page_information=page_information,
            sort_information=sort_information
        )

        if page_information:
            transformed_data = transform_data(
                'donate/donors/{}'.format( donor_type ),
                page_information,
                donors,
                CagedDonorSchema
            )
            response = jsonify( transformed_data[ 'page' ] )
            response.headers[ 'Link' ] = transformed_data[ 'link-header' ]
            response.status_code = 200
            return response

        if donor_type == 'caged':
            schema = CagedDonorSchema( many=True )
        else:
            schema = QueuedDonorSchema( many=True )

        result = schema.dump( donors ).data

        return result, 200


def is_hex_string( searchable_id ):
    """

    :param searchable_id:
    :return:
    """
    if not test_hex_string( searchable_id ):
        raise TypeError
    return True, 200
