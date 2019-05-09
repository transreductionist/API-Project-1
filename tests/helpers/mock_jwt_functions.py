"""A helper module to define mocks for the Ultsys endpoints: find, create, and update."""
# pylint: disable=too-few-public-methods

ACCESS_TOKEN = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2NsYWltcyI6eyJ1bHRzeXNfaWQiOjMyNTUxNjIsInJvbGVzIjpbInJlYWQiLCJzdXBlcmFkbWluIiwiYWRtaW4iLCJiYXNpY191c2VyIl19LCJqdGkiOiI5M2Q1NTZlOS1hNDU5LTQ3ZGEtOTZkMC03Mjg3YjYxZDEyMzUiLCJleHAiOjk5OTk5OTk5OTk5LCJmcmVzaCI6ZmFsc2UsImlhdCI6MTU0MDQ5NTg2MiwidHlwZSI6ImFjY2VzcyIsIm5iZiI6MTU0MDQ5NTg2MiwiaWRlbnRpdHkiOiJhcGV0ZXJzQG51bWJlcnN1c2EuY29tIn0.0dBGyCZXCytLdhNaeAcnf-FvCSRmi9Bqwf6jMeEegpVG-FwMFt8ENIgJMGhpN_Y0yo00WYPygsMFotJTQXJ85coXO7HsboIMiG5i_HpaGKRzFowg75CjLPtX7JEOqijlvUs2XQ_nt-WtNA0EH2-EBp00s2gV7KCPC1D2FGMPwF_d6QLE1gJ8EhqKj6LGEtkt1b8aoFZgC9Jkk8uAPddRXmhZCCRqlFO4udXHWOldvjNbD7sPWsKh_9_hr8mrL1x1QP1Vlj519Mij5xLiXtGLftT-bkTwvBisNHYrQjVcPoDN1Bv1t5OcaE-KgwIrbYfoFYwNDp9zhG3eZtxi3vep_w'  # noqa: E501 pylint: disable=line-too-long

JWT_DATA = {
    'user_claims': { 'ultsys_id': 3255162, 'roles': [ 'read', 'superadmin', 'admin', 'basic_user' ] },
    'jti': '93d556e9-a459-47da-96d0-7287b61d1235',
    'exp': 99999999999,
    'fresh': False,
    'iat': 1540495862,
    'type': 'access',
    'nbf': 1540495862,
    'identity': 'apeters@numbersusa.com'
}


def mock_verify_jwt_in_request():
    """The mocked function for verify_jwt_in_request used in checking JWT tokens.

    The function verify_jwt_in_request can be found at:

        from nusa_jwt_auth import verify_jwt_in_request

    :return:
    """


def mock_manage_jwt_claims( *args ):  # pylint: disable=unused-argument
    """The mocked function for manage_jwt_claims used in checking JWT tokens.

    :return: claim data
    """

    return JWT_DATA[ 'user_claims' ]
