"""The model for gift_thank_you_letter table"""
# pylint: disable=R0903
# pylint: disable=nusa-whitespace-checker
from sqlalchemy.ext.hybrid import hybrid_property

from application.flask_essentials import database
from application.helpers.ultsys_user import get_ultsys_user
from application.models.gift import GiftModel


class GiftThankYouLetterModel( database.Model ):
    """A gift thank you model"""

    __tablename__ = 'gift_thank_you_letter'
    id = database.Column( database.Integer, primary_key=True, autoincrement=True, nullable=False )
    gift_id = database.Column( database.Integer, nullable=False )
    gift = database.relationship(
        'GiftModel',
        foreign_keys=[ GiftModel.id ],
        primaryjoin='GiftThankYouLetterModel.gift_id == GiftModel.id',
        uselist=False
    )

    @hybrid_property
    def user( self ):
        """Hybrid user attribute"""
        try:
            user = get_ultsys_user( { 'ID': { 'eq': self.gift.user_id } } ).json()[ 0 ]
        except (AttributeError, IndexError, KeyError):
            user = None
        if user:
            return {
                'firstname': user[ 'firstname' ],
                'lastname': user[ 'lastname' ],
                'address': user[ 'address' ],
                'city': user[ 'city' ],
                'state': user[ 'state' ],
                'email': user[ 'email' ],
            }
        return None
