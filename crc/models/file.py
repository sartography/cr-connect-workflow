import enum

from marshmallow_enum import EnumField
from marshmallow_sqlalchemy import ModelSchema
from sqlalchemy import func

from crc import db


class FileType(enum.Enum):
    bpmn = "bpmm"
    svg = "svg"
    dmn = "dmn"
#    docx = "docx"


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
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'))
#    workflow_id = db.Column(db.String, db.ForeignKey('workflow.id'))


class FileModelSchema(ModelSchema):
    class Meta:
        model = FileModel
        include_fk = True  # Includes foreign keys
    type = EnumField(FileType)


