import enum

from flask_marshmallow.sqla import ModelSchema
from marshmallow_enum import EnumField
from sqlalchemy import func

from crc import db


class FileType(enum.Enum):
    bpmn = "bpmm"
    svg = "svg"
    dmn = "dmn"


class FileDataModel(db.Model):
    __tablename__ = 'file_data'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.LargeBinary)
    file_model_id = db.Column(db.Integer, db.ForeignKey('file.id'))
    file_model = db.relationship("FileModel")

class FileModel(db.Model):
    __tablename__ = 'file'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    version = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime(timezone=True), default=func.now())
    type = db.Column(db.Enum(FileType))
    primary = db.Column(db.Boolean)
    content_type = db.Column(db.String)
    workflow_spec_id = db.Column(db.Integer, db.ForeignKey('workflow_spec.id'))


class FileSchema(ModelSchema):
    class Meta:
        model = FileModel
    type = EnumField(FileType)


