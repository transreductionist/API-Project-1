"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
from application.models.agent import AgentModel
from application.models.gift import GiftModel
from application.models.transaction import TransactionModel

MODELS_WITH_ENUMERATIONS = {
    'giftmodel': GiftModel,
    'transactionmodel': TransactionModel,
    'agentmodel': AgentModel
}


def get_enumeration( model, attribute ):
    """Simple query to return the enumeration values for a model and its attribute.

    :param model: The model to find enumeration values on.
    :param attribute: The enumeration attribute on the model.
    :return: An enumeration list.
    """

    try:
        enumeration_list = getattr( MODELS_WITH_ENUMERATIONS[ model ], attribute ).property.columns[ 0 ].type.enums
        return enumeration_list
    except AttributeError as error:
        error.args = ( 'The enumeration for the attribute requested does not exist.', )
        raise error
    except KeyError as error:
        error.args = ( 'KeyError: Model key does not exist.', )
        raise error
