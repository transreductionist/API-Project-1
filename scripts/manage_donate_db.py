"""The following script will DROP ALL tables and then CREATE ALL.

Use with caution! It will remove all existing data, and then reconstruct the tables with no entries. Other functions
can be added to manage other database tasks. To run a function navigate to the project root and, for example, on the
command line type:

python -c "import scripts.manage_donate_db;scripts.manage_donate_db.drop_all_and_create()"
python -c "import scripts.manage_donate_db;scripts.manage_donate_db.create_database_tables()"
python -c "import scripts.manage_donate_db;scripts.manage_donate_db.create_gift_and_transaction()"
"""
import uuid
from datetime import datetime
from datetime import timedelta
from decimal import Decimal

from application.app import create_app
from application.flask_essentials import database
from application.schemas.agent import AgentSchema
from application.schemas.gift import GiftSchema
from application.schemas.transaction import TransactionSchema
from tests.helpers.default_dictionaries import get_gift_dict
from tests.helpers.default_dictionaries import get_transaction_dict

app = create_app( 'DEV' )  # pylint: disable=C0103


def drop_all_and_create():
    """A function to drop and then recreate the database tables."""

    with app.app_context():
        database.reflect()
        database.drop_all()
        database.create_all()


def create_database_tables():
    """A function to create the DONATE database tables, specifically the GiftModel with UUID.

    The GiftModel is build using Marshmallow schema GiftSchema, which deserializes a dictionary to the model:
    The searchable_id in the gift_json is:
        gift_json[ 'searchable_id' ] = uuid.uuid4()
    This gets passed to the GiftSchema where:
        searchable_id = fields.UUID()
    And so the validation step is passed.
    MySql does not have a UUID type though and there we have ( GiftModel ):
        searchable_id = database.Column( database.BINARY( 16 ), nullable=False, default=uuid.uuid4().bytes )
    The helper model class BinaryUUID in binary_uuid.py handles the serialization in and out.
    """

    with app.app_context():

        type = { 3: 'Gift', 2: 'Deposit to Bank', 1: 'Dispute', 0: 'Refund' }
        # Create 100 gifts.
        for i in range( 0, 100 ):
            gift_json = get_gift_dict()
            del gift_json[ 'id' ]
            gift_json[ 'searchable_id' ] = uuid.uuid4()
            gift_model = GiftSchema().load( gift_json ).data

            # Add the index as a note for debugging Gifts, since they exclude ID.
            gift_model.notes = '{} : {}'.format( str( i + 1 ), str( gift_json[ 'searchable_id' ] ) )

            database.session.add( gift_model )
            database.session.flush()
            gift_id = gift_model.id

            # Create 4 transactions per each gift.
            transactions = []
            start_datetime = datetime.utcnow()
            for j in range( 0, 4 ):  # pylint: disable=unused-variable
                test_datetime = start_datetime - timedelta( days=j )
                test_datetime = test_datetime.strftime( '%Y-%m-%d %H:%M:%S' )
                transaction_json = get_transaction_dict( {
                    'gift_id': gift_id,
                    'date_in_utc': test_datetime,
                    'gross_gift_amount': Decimal( 25 - j ),
                    'type': type[ j ],
                    'status': 'Completed'
                } )
                del transaction_json[ 'id' ]
                transaction_model = TransactionSchema().load( transaction_json ).data
                transactions.append( transaction_model )
            database.session.bulk_save_objects( transactions )

        # Create the agents.
        # agent_jsons = [
        #     { 'name': 'Donate API', 'user_id': None, 'staff_id': None, 'type': 'Automated' },
        #     { 'name': 'Braintree', 'user_id': None, 'staff_id': None, 'type': 'Organization' },
        #     { 'name': 'PayPal', 'user_id': None, 'staff_id': None, 'type': 'Organization' },
        #     { 'name': 'Credit Card Issuer', 'user_id': None, 'staf_id': None, 'type': 'Organization' },
        #     { 'name': 'Unspecified NumbersUSA Staff', 'user_id': None, 'staff_id': None, 'type': 'Staff Member' },
        #     { 'name': 'Dan Marsh', 'user_id': 1234, 'staff_id': 4321, 'type': 'Staff Member' },
        #     { 'name': 'Joshua Turcotte', 'user_id': 7041, 'staff_id': 1407, 'type': 'Staff Member' },
        #     { 'name': 'Donate API', 'user_id': None, 'staff_id': None, 'type': 'Automated' }
        # ]
        # agents = []
        # for agent_json in agent_jsons:
        #     agent_model = AgentSchema().load( agent_json ).data
        #     agents.append( agent_model )
        # database.session.bulk_save_objects( agents )

        database.session.commit()


def create_agent_table():
    """A function to create the DONATE database AgentModel table."""

    with app.app_context():
        drop_all_and_create()

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
        database.session.bulk_save_objects( agents )

        database.session.commit()


def create_gift_and_transaction():
    """A function to create a gift and an attached transaction for a given Braintree sale.

    Sometimes while testing a developer will need to have a specific gift and transaction in the database that
    would have been created for a Braintree sale. This function allows you to specify Braintree reference numbers,
    e.g. transaction sale ID and the subscription reference number, and create the gift and transaction associated
    with that sale.
    """

    with app.app_context():

        # These are the Braintree subscription ID and transaction sale ID to create a gift and transaction for.
        # Change this to suit your needs.
        subscription_id = 'kfwgzr'
        transaction_id = '83afbynd'

        date_start = datetime.utcnow().replace( hour=23, minute=59, second=59, microsecond=9999 )
        utc_dates = [ date_start - timedelta( hours=hours, minutes=30 ) for hours in range( 1, 25 ) ]

        pairs = 1
        for date_in_utc in utc_dates:
            i = 0
            while i < pairs:
                i += 1
                # Create a gift.
                gift_json = get_gift_dict( { 'recurring_subscription_id': subscription_id } )
                gift_json[ 'searchable_id' ] = uuid.uuid4()
                del gift_json[ 'id' ]

                gift_model = GiftSchema().load( gift_json ).data

                database.session.add( gift_model )
                database.session.flush()
                gift_id = gift_model.id

                # Create 4 transactions per each gift.
                transaction_json = get_transaction_dict( { 'gift_id': gift_id } )
                transaction_json[ 'type' ] = 'Gift'
                transaction_json[ 'status' ] = 'Completed'
                del transaction_json[ 'id' ]
                transaction_model = TransactionSchema().load( transaction_json ).data
                transaction_model.reference_number = transaction_id
                transaction_model.date_in_utc = date_in_utc

                transaction_model.reference_number = transaction_id
                transaction_model.notes = '{} : {}'.format( str( 1 ), str( gift_json[ 'searchable_id' ] ) )
                database.session.add( transaction_model )

        database.session.commit()
