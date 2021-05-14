from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from marshmallow import EXCLUDE
from marshmallow_sqlalchemy import ModelSchema
from sqlalchemy import func
import marshmallow
from marshmallow import INCLUDE, fields

from crc import db, ma

class DataStoreModel(db.Model):
    __tablename__ = 'data_store'
    id = db.Column(db.Integer, primary_key=True)
    last_updated = db.Column(db.DateTime(timezone=True), server_default=func.now())
    key = db.Column(db.String, nullable=False)
    workflow_id = db.Column(db.Integer)
    study_id = db.Column(db.Integer, nullable=True)
    task_id = db.Column(db.String)
    spec_id = db.Column(db.String)
    user_id = db.Column(db.String, nullable=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=True)
    value = db.Column(db.String)


class DataStoreSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = DataStoreModel
        load_instance = True
        sqla_session = db.session
