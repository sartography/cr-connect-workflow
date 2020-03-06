import enum

from marshmallow_enum import EnumField
from marshmallow_sqlalchemy import ModelSchema
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID

from crc import db


class FileType(enum.Enum):
    bpmn = "bpmm"
    csv = 'csv'
    dmn = "dmn"
    doc = "doc"
    docx = "docx"
    gif = 'gif'
    jpg = 'jpg'
    md = 'md'
    pdf = 'pdf'
    png = 'png'
    ppt = 'ppt'
    pptx = 'pptx'
    rtf = 'rtf'
    svg = "svg"
    svg_xml = "svg+xml"
    txt = 'txt'
    xls = 'xls'
    xlsx = 'xlsx'
    xml = 'xml'
    zip = 'zip'


CONTENT_TYPES = {
    "bpmn":  "text/xml",
    "csv": "text/csv",
    "dmn": "text/xml",
    "doc": "application/msword",
    "docx":  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "gif": "image/gif",
    "jpg": "image/jpeg",
    "md" : "text/plain",
    "pdf": "application/pdf",
    "png": "image/png",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx":  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "rtf": "application/rtf",
    "svg": "image/svg+xml",
    "svg_xml": "image/svg+xml",
    "txt": "text/plain",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xml": "application/xml",
    "zip": "application/zip"
}

class FileDataModel(db.Model):
    __tablename__ = 'file_data'
    id = db.Column(db.Integer, primary_key=True)
    md5_hash = db.Column(UUID(as_uuid=True), unique=False, nullable=False)
    data = db.Column(db.LargeBinary)
    version = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime(timezone=True), default=func.now())
    file_model_id = db.Column(db.Integer, db.ForeignKey('file.id'))
    file_model = db.relationship("FileModel")


class FileModel(db.Model):
    __tablename__ = 'file'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    type = db.Column(db.Enum(FileType))
    primary = db.Column(db.Boolean)
    content_type = db.Column(db.String)
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'), nullable=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=True)
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'), nullable=True)
    task_id = db.Column(db.String, nullable=True)
    form_field_key = db.Column(db.String, nullable=True)
    latest_version = db.Column(db.Integer, default=0)


class FileModelSchema(ModelSchema):
    class Meta:
        model = FileModel
        include_fk = True  # Includes foreign keys
    type = EnumField(FileType)
