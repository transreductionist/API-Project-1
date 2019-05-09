This category strictly contains model mappings to individual data tables, document stores, caches, etc.

Tables are explicitly named. The user table is a stand-in for the final database table to be used for this model.
Notice that the database=SQLAlchemy() is done through the import of flask_essentials. This will keep the Marshmallow
and model SQLAlchemy sessions the same.

# List of Schemas

## agent.py

Marshmallow schema for serialization/deserialization of AgentModel.

## braintree_customer.py

Marshmallow schema for serialization/deserialization of a Braintree customer. The complete object is not mapped here,
and only the fields required.

## braintree_sale.py

Marshmallow schema for serialization/deserialization of a Braintree Transaction.sale(). The Braintree transaction
object has multiple and nested fields, all of which are not required. This schema maps only the fields that are
required by the application.

## caged_donor.py

Marshmallow schema for serialization/deserialization of CagedDonorModel.

## campaign.py

Marshmallow schema for serialization/deserialization of CampaignModel.

## gift.py

Marshmallow schema for serialization/deserialization of GiftModel.

## transaction.py

Marshmallow schema for serialization/deserialization of TransactionModel.
