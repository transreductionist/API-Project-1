This category strictly contains model mappings to individual data tables, document stores, caches, etc.

Tables are explicitly named. The user table is a stand-in for the final database table to be used for this model.
Notice that the database=SQLAlchemy() is done through the import of flask_essentials. This will keep the Marshmallow
and model SQLAlchemy sessions the same.

# List of Models

## agent.py

The model for the Donations API service: agent table.

## caged_donor.py

The model for the Donations API service: caged_donor table.

## campaign.py

The model for the Donations API service: campaigns.

## gift.py

The model for the Donations API service: gift table.

## transaction.py

The model for the Donations API service: transaction table.
