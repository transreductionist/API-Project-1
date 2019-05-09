"""Create the method used model."""
from application.models.method_used import MethodUsedModel


def create_method_used():
    """Create the methods used.

    :return: The list of MethodUsedModels.
    """

    method_used_models = list()
    method_used_models.append( MethodUsedModel( id=1, name='Web Form Credit Card', billing_address_required=1 ) )
    method_used_models.append( MethodUsedModel( id=2, name='Admin-Entered Credit Card', billing_address_required=1 ) )
    method_used_models.append( MethodUsedModel( id=3, name='Check', billing_address_required=0 ) )
    method_used_models.append( MethodUsedModel( id=4, name='Money Order', billing_address_required=0 ) )
    method_used_models.append( MethodUsedModel( id=5, name='Stock', billing_address_required=0 ) )
    method_used_models.append( MethodUsedModel( id=6, name='Cash', billing_address_required=0 ) )
    method_used_models.append( MethodUsedModel( id=7, name='Wire Transfer', billing_address_required=0 ) )
    method_used_models.append( MethodUsedModel( id=8, name='Other', billing_address_required=0 ) )
    method_used_models.append( MethodUsedModel( id=9, name='Web Form PayPal', billing_address_required=0 ) )
    method_used_models.append( MethodUsedModel( id=10, name='Web Form Venmo', billing_address_required=0 ) )
    method_used_models.append( MethodUsedModel( id=11, name='Web Form ApplePay', billing_address_required=0 ) )
    method_used_models.append( MethodUsedModel( id=12, name='Unkown Method Used', billing_address_required=0 ) )

    return method_used_models
