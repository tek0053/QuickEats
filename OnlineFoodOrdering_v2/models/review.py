from . import db
from sqlalchemy import Sequence
from datetime import datetime


class Review(db.Model):
    __bind_key__ = 'db'
    id = db.Column(db.Integer, Sequence('Review_sequence'), unique=True, nullable=False, primary_key=True)
    user_id = db.Column(db.Integer)
    menu_item_id = db.Column(db.Integer)
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    review_date = db.Column(db.TIMESTAMP, default=datetime.now)
