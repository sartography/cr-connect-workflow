from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from marshmallow import EXCLUDE
from sqlalchemy import func

from crc import db

class DataStoreModel(db.Model):
    __tablename__ = 'data_store'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String)
    workflow_id = db.Column(db.Integer)
    study_id = db.Column(db.Integer)
    task_id = db.Column(db.String)
    spec_id = db.Column(db.String)
    user_id = db.Column(db.String)
    value = db.Column(db.String)
