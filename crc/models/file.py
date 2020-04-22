import enum
from typing import cast

from marshmallow_enum import EnumField
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import func, Index, text
from sqlalchemy.dialects import postgresql
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
    is_status = db.Column(db.Boolean)
    content_type = db.Column(db.String)
    is_reference = db.Column(db.Boolean, nullable=False, default=False) # A global reference file.
    primary = db.Column(db.Boolean, nullable=False, default=False) # Is this the primary BPMN in a workflow?
    primary_process_id = db.Column(db.String, nullable=True) # An id in the xml of BPMN documents, critical for primary BPMN.
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'), nullable=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=True)
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'), nullable=True)
    task_id = db.Column(db.String, nullable=True)
    irb_doc_code = db.Column(db.String, nullable=True) # Code reference to the irb_documents.xlsx reference file.
    form_field_key = db.Column(db.String, nullable=True)
    latest_version = db.Column(db.Integer, default=0)


class FileModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = FileModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys
    type = EnumField(FileType)


class LookupFileModel(db.Model):
    """Takes the content of a file (like a xlsx, or csv file) and creates a key/value
    store that can be used for lookups and searches. This table contains the metadata,
    so we know the version of the file that was used, and what key column, and value column
    were used to generate this lookup table.  ie, the same xls file might have multiple
    lookup file models, if different keys and labels are used - or someone decides to
    make a change.  We need to handle full text search over the label and value columns,
    and not every column, because we don't know how much information will be in there. """
    __tablename__ = 'lookup_file'
    id = db.Column(db.Integer, primary_key=True)
    label_column = db.Column(db.String)
    value_column = db.Column(db.String)
    file_data_model_id = db.Column(db.Integer, db.ForeignKey('file_data.id'))


class LookupDataModel(db.Model):
    __tablename__ = 'lookup_data'
    id = db.Column(db.Integer, primary_key=True)
    lookup_file_model_id = db.Column(db.Integer, db.ForeignKey('lookup_file.id'))
    lookup_file_model = db.relationship(LookupFileModel)
    value = db.Column(db.String)
    label = db.Column(db.String)
    # In the future, we might allow adding an additional "search" column if we want to search things not in label.
    data = db.Column(db.JSON) # all data for the row is stored in a json structure here, but not searched presently.

    # Assure there is a searchable index on the label column, so we can get fast results back.
    # query with:
    # search_results = LookupDataModel.query.filter(LookupDataModel.label.match("INTERNAL")).all()

    __table_args__ = (
        Index(
            'ix_lookupdata_tsv',
            func.to_tsvector('english', label),
            postgresql_using='gin'
            ),
        )

