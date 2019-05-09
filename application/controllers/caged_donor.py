"""Controllers for Flask-RESTful resources: handle the business logic for the endpoint."""
from application.models.caged_donor import CagedDonorModel


def get_caged_donors():
    """Simple query to return all caged donors."""

    caged_donors = CagedDonorModel.query.all()
    return caged_donors
