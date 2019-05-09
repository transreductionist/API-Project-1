"""A module to facilitate serailization and deserialization of a model given their schema."""
import uuid


def from_json( model_schema, model_dictionary, create=True ):
    """Takes the model_dictionary and deserializes it into the model using its Marshmallow schema: model_schema.
    SQLAlchemy database.session.add() creates a new object if an ID is not provided, and updates an object if an ID is
    provided. Which operation is performed is determined by the value of create. If create is true, the ID is removed
    from the fields of the Model. If create is False, the model will be updated, and the dictionary must have the ID.
    :param obj model_schema: This is a Marshmallow schema to be used for 2-way serialization.
    :param dict model_dictionary: The dictionary that is to be serialized ( deserialized ) by the schema.
    :param bool create: Whether create or update the model. Default is to create.
    :return: The Marshaled object.
    """

    fields = [ column.key for column in model_schema.Meta.model.__table__.columns ]
    model_json = {}
    if create:
        # The key 'id' is used for local databases. The key 'ID' is used for the Ultsys user.
        if 'id' in fields:
            fields.remove( 'id' )
        elif 'ID' in fields:
            fields.remove( 'ID' )
        # If you create a gift the searchable_id must be in the model_dictionary.
        if 'searchable_id' in fields:
            model_json[ 'searchable_id' ] = uuid.uuid4()

    for field in fields:
        # If you update a gift do not allow the update of the searchable_id if it is in the model_dictionary.
        if field in model_dictionary and field != 'searchable_id':
            model_json[ field ] = model_dictionary[ field ]

    model = model_schema.load( model_json )
    return model


def to_json( model_schema, model ):
    """Serializes the model given its Schema"""

    model_json = model_schema.dump( model )
    return model_json
