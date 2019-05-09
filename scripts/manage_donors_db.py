"""The following script will DROP ALL tables and then CREATE ALL.

Use with caution! It will remove all existing data, and then reconstruct the tables with no entries. Other functions
can be added to manage other database tasks. To run a function navigate to the project root and, for example, on the
command line type:

python -c "import scripts.manage_donors_db;scripts.manage_donors_db.drop_all_and_create()"
python -c "import scripts.manage_donors_db;scripts.manage_donors_db.create_database_tables()"
"""
import uuid

from application.app import create_app
from application.flask_essentials import database
from application.schemas.agent import AgentSchema
from application.schemas.caged_donor import CagedDonorSchema
from application.schemas.queued_donor import QueuedDonorSchema
from tests.helpers.default_dictionaries import get_caged_donor_dict

app = create_app( 'DEV' )  # pylint: disable=C0103


def drop_all_and_create():
    """A function to drop and then recreate the database tables."""

    with app.app_context():
        database.reflect()
        database.drop_all()
        database.create_all()


def create_database_tables():
    """Function to create the DONATE database tables, specifically the CagedDonorModel and QueuedDonorModel with UUID.

    All that is said here for the CagedDonorModel also holds for the QueuedDonorModel. The CagedDonorModel is built
    using Marshmallow schema CagedDonorSchema, which deserializes a dictionary to the model. The searchable_id in the
    donor_json is:
        donor_json[ 'searchable_id' ] = uuid.uuid4()
    This gets passed to the CagedDonorSchema where:
        searchable_id = fields.UUID()
    And so the validation step is passed.
    MySql does not have a UUID type though and there we have ( CagedDonorModel ):
        searchable_id = database.Column( database.BINARY( 16 ), nullable=False, default=uuid.uuid4().bytes )
    The helper model class BinaryUUID in binary_uuid.py handles the serialization in and out.
    """

    with app.app_context():
        drop_all_and_create()

        caged_donors = []
        queued_donors = []
        # Create 100 caged donors.
        for i in range( 0, 100 ):
            donor_json = get_caged_donor_dict( { 'gift_searchable_id': uuid.uuid4() } )
            donor_json[ 'gift_id' ] = i + 1
            donor_json[ 'customer_id' ] = str( ( i + 1 ) + 1000 )
            del donor_json[ 'id' ]

            caged_donor = CagedDonorSchema().load( donor_json ).data
            queued_donor = QueuedDonorSchema().load( donor_json ).data

            caged_donors.append( caged_donor )
            queued_donors.append( queued_donor )

        # Create the agents.
        agent_jsons = [
            { 'name': 'Donate API', 'user_id': None, 'staff_id': None, 'type': 'Automated' },
            { 'name': 'Braintree', 'user_id': None, 'staff_id': None, 'type': 'Organization' },
            { 'name': 'PayPal', 'user_id': None, 'staff_id': None, 'type': 'Organization' },
            { 'name': 'Credit Card Issuer', 'user_id': None, 'staf_id': None, 'type': 'Organization' },
            { 'name': 'Unspecified NumbersUSA Staff', 'user_id': None, 'staff_id': None, 'type': 'Staff Member' },
            { 'name': 'Dan Marsh', 'user_id': 1234, 'staff_id': 4321, 'type': 'Staff Member' },
            { 'name': 'Joshua Turcotte', 'user_id': 7041, 'staff_id': 1407, 'type': 'Staff Member' },
            { 'name': 'Donate API', 'user_id': None, 'staff_id': None, 'type': 'Automated' }
        ]
        agents = []
        for agent_json in agent_jsons:
            agent_model = AgentSchema().load( agent_json ).data
            agents.append( agent_model )

        database.session.bulk_save_objects( caged_donors )
        database.session.bulk_save_objects( queued_donors )
        database.session.bulk_save_objects( agents )

        database.session.commit()
