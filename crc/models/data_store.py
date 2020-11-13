from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from marshmallow import EXCLUDE
from sqlalchemy import func
import marshmallow
from marshmallow import INCLUDE, fields

from crc import db, ma

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


class DataStoreSchema(ma.Schema):
    id = fields.Integer(required=False)
    key = fields.String(required=True)
    workflow_id = fields.Integer()
    study_id = fields.Integer()
    task_id = fields.String()
    spec_id = fields.String()
    user_id = fields.String()
    value = fields.String()
