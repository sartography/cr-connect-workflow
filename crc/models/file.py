import enum
import urllib

import flask
from flask import url_for
from marshmallow import INCLUDE, EXCLUDE, Schema
from marshmallow.fields import Method
from marshmallow_enum import EnumField
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import deferred, relationship

from crc import db, ma
from crc.models.data_store import DataStoreModel


class FileType(enum.Enum):
    bpmn = "bpmn"
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
    "md": "text/plain",
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


class DocumentModel(db.Model):
    __tablename__ = 'document'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    type = db.Column(db.String, nullable=False)
    content_type = db.Column(db.String, nullable=False)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=True)
    task_spec = db.Column(db.String, nullable=True)
    irb_doc_code = db.Column(db.String, nullable=False)  # Code reference to the documents.xlsx reference file.
    # TODO: Fix relationship with data_store table, then add this back in
    data_stores = relationship(DataStoreModel, cascade="all,delete", backref="document")
    md5_hash = db.Column(UUID(as_uuid=True), unique=False, nullable=False)
    data = deferred(db.Column(db.LargeBinary))  # Don't load it unless you have to.
    # TODO: Determine whether size is used (in frontend/bpmn)
    # size = db.Column(db.Integer, default=0)  # Do we need this?
    date_modified = db.Column(db.DateTime(timezone=True), onupdate=func.now())
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    user_uid = db.Column(db.String, db.ForeignKey('user.uid'), nullable=True)
    archived = db.Column(db.Boolean, default=False)


class FileDataModel(db.Model):
    __tablename__ = 'file_data'
    id = db.Column(db.Integer, primary_key=True)
    md5_hash = db.Column(UUID(as_uuid=True), unique=False, nullable=False)
    data = deferred(db.Column(db.LargeBinary))  # Don't load it unless you have to.
    version = db.Column(db.Integer, default=0)
    size = db.Column(db.Integer, default=0)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    file_model_id = db.Column(db.Integer, db.ForeignKey('file.id'))
    file_model = db.relationship("FileModel", foreign_keys=[file_model_id])
    user_uid = db.Column(db.String, db.ForeignKey('user.uid'), nullable=True)


class FileModel(db.Model):
    __tablename__ = 'file'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    type = db.Column(db.Enum(FileType))
    content_type = db.Column(db.String)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=True)
    task_spec = db.Column(db.String, nullable=True)
    irb_doc_code = db.Column(db.String, nullable=True)  # Code reference to the documents.xlsx reference file.
    # data_stores = relationship(DataStoreModel, cascade="all,delete", backref="file")


class File(object):
    def __init__(self):
        self.content_type = None
        self.name = None
        self.content_type = None
        self.workflow_id = None
        self.irb_doc_code = None
        self.type = None
        self.document = {}
        self.last_modified = None
        self.size = None
        self.data_store = {}

    @classmethod
    def from_document_model(cls, document_model: DocumentModel, doc_dictionary):
        if document_model.irb_doc_code and document_model.irb_doc_code in doc_dictionary:
            document = doc_dictionary[document_model.irb_doc_code]
        else:
            document = {}
        instance = cls()
        instance.id = document_model.id
        instance.name = document_model.name
        instance.content_type = document_model.content_type
        instance.workflow_id = document_model.workflow_id
        instance.irb_doc_code = document_model.irb_doc_code
        instance.type = document_model.type
        instance.document = document
        instance.last_modified = document_model.date_modified
        instance.size = None
        instance.data_store = {}

        return instance

    @classmethod
    def from_file_system(cls, file_name, file_type, content_type,
                         last_modified, file_size):

        instance = cls()
        instance.name = file_name
        instance.content_type = content_type
        instance.type = file_type
        instance.document = {}
        instance.last_modified = last_modified
        instance.size = file_size
        #fixme:  How to track the user id?
        instance.data_store = {}
        return instance


class DocumentModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = DocumentModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys
        unknown = EXCLUDE


class FileModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = FileModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys
        unknown = EXCLUDE
    type = EnumField(FileType)


class FileSchema(Schema):
    class Meta:
        model = File
        fields = ["id", "name", "content_type", "workflow_id",
                  "irb_doc_code", "last_modified", "type",
                  "size", "data_store", "document", "user_uid", "url"]
        unknown = INCLUDE
    url = Method("get_url")

    def get_url(self, obj):
        token = 'not_available'
        if hasattr(obj, 'id') and obj.id is not None:
            file_url = url_for("/v1_0.crc_api_file_refactor_get_file_data_link", file_id=obj.id, _external=True)
            if hasattr(flask.g, 'user'):
                token = flask.g.user.encode_auth_token()
            url = file_url + '?auth_token=' + urllib.parse.quote_plus(token)
            return url
        else:
            return ""


class LookupFileModel(db.Model):
    """Gives us a quick way to tell what kind of lookup is set on a form field."""
    __tablename__ = 'lookup_file'
    id = db.Column(db.Integer, primary_key=True)
    workflow_spec_id = db.Column(db.String)
    task_spec_id = db.Column(db.String)
    field_id = db.Column(db.String)
    file_name = db.Column(db.String)
    file_timestamp = db.Column(db.FLOAT)  # The file systems time stamp, to check for changes to the file.
    is_ldap = db.Column(db.Boolean)  # Allows us to run an ldap query instead of a db lookup.
    dependencies = db.relationship("LookupDataModel", lazy="select", backref="lookup_file_model",
                                   cascade="all, delete, delete-orphan")


class LookupDataModel(db.Model):
    __tablename__ = 'lookup_data'
    id = db.Column(db.Integer, primary_key=True)
    lookup_file_model_id = db.Column(db.Integer, db.ForeignKey('lookup_file.id'))
    value = db.Column(db.String)
    label = db.Column(db.String)
    # In the future, we might allow adding an additional "search" column if we want to search things not in label.
    data = db.Column(db.JSON)  # all data for the row is stored in a json structure here, but not searched presently.

    # Assure there is a searchable index on the label column, so we can get fast results back.
    # query with:
    # search_results = LookupDataModel.query.filter(LookupDataModel.label.match("INTERNAL")).all()

    __ts_vector__ = func.to_tsvector('simple', label)

    __table_args__ = (
        Index(
            'ix_lookupdata_tsv',
            __ts_vector__,  # Use simple, not english to keep stop words in place.
            postgresql_using='gin'
            ),
        )


class LookupDataSchema(ma.Schema):
    class Meta:
        model = LookupDataModel
        load_instance = True
        include_relationships = False
        include_fk = False  # Includes foreign keys
        exclude = ['id']  # Do not include the id field, it should never be used via the API.


class SimpleFileSchema(ma.Schema):

    class Meta:
        model = DocumentModel
        fields = ["name"]
