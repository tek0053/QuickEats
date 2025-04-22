from . import db
from sqlalchemy import Sequence
from datetime import datetime


class MenuItem(db.Model):
    __bind_key__ = 'db'
    id = db.Column(db.Integer, Sequence('MenuItem_sequence'), unique=True, nullable=False, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(255))
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer)
    stock = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(255))
    availability = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer)
    created_at = db.Column(db.TIMESTAMP, default=datetime.now)
