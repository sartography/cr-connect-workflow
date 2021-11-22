import enum
import urllib

import connexion
import flask
from flask import url_for
from marshmallow import INCLUDE, EXCLUDE, Schema
from marshmallow.fields import Method
from marshmallow_enum import EnumField
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from sqlalchemy import func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import deferred, relationship

from crc import db, ma, app
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


class FileDataModel(db.Model):
    __tablename__ = 'file_data'
    id = db.Column(db.Integer, primary_key=True)
    md5_hash = db.Column(UUID(as_uuid=True), unique=False, nullable=False)
    sha = db.Column(db.String, nullable=True) # this is the sha of the actual data
    data = deferred(db.Column(db.LargeBinary))  # Don't load it unless you have to.
    version = db.Column(db.Integer, default=0)
    size = db.Column(db.Integer, default=0)
    date_created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    file_model_id = db.Column(db.Integer, db.ForeignKey('file.id'))
    file_model = db.relationship("FileModel", foreign_keys=[file_model_id])
    user_uid = db.Column(db.String, db.ForeignKey('user.uid'), nullable=True)


class FileDataModelSchema(Schema):
    class Meta:
        model = FileDataModel
        fields = ["id", "md5_hash", "sha", "data", "version", "size", "date_created", "file_model_id", "file_model", "user_uid"]



class FileModel(db.Model):
    __tablename__ = 'file'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    type = db.Column(db.Enum(FileType))
    is_status = db.Column(db.Boolean)
    content_type = db.Column(db.String)
    is_reference = db.Column(db.Boolean, nullable=False, default=False)  # A global reference file.
    primary = db.Column(db.Boolean, nullable=False, default=False)  # Is this the primary BPMN in a workflow?
    primary_process_id = db.Column(db.String, nullable=True)  # An id in the xml of BPMN documents, for primary BPMN.
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'), nullable=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=True)
    task_spec = db.Column(db.String, nullable=True)
    irb_doc_code = db.Column(db.String, nullable=True)  # Code reference to the irb_documents.xlsx reference file.
    # A request was made to delete the file, but we can't because there are
    # active approvals or running workflows that depend on it.  So we archive
    # it instead, hide it in the interface.
    is_review = db.Column(db.Boolean, default=False, nullable=True)
    archived = db.Column(db.Boolean, default=False, nullable=False)
    data_stores = relationship(DataStoreModel, cascade="all,delete", backref="file")


class File(object):
    @classmethod
    def from_models(cls, model: FileModel, data_model: FileDataModel, doc_dictionary):
        instance = cls()
        instance.id = model.id
        instance.name = model.name
        instance.is_status = model.is_status
        instance.is_reference = model.is_reference
        instance.content_type = model.content_type
        instance.primary = model.primary
        instance.primary_process_id = model.primary_process_id
        instance.workflow_spec_id = model.workflow_spec_id
        instance.workflow_id = model.workflow_id
        instance.irb_doc_code = model.irb_doc_code
        instance.type = model.type
        if model.irb_doc_code and model.irb_doc_code in doc_dictionary:
            instance.document = doc_dictionary[model.irb_doc_code]
        else:
            instance.document = {}
        if data_model:
            instance.last_modified = data_model.date_created
            instance.latest_version = data_model.version
            instance.size = data_model.size
            instance.user_uid = data_model.user_uid
        else:
            instance.last_modified = None
            instance.latest_version = None

        instance.data_store = {}
        for ds in model.data_stores:
            instance.data_store[ds.key] = ds.value

        return instance


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
        fields = ["id", "name", "is_status", "is_reference", "content_type",
                  "primary", "primary_process_id", "workflow_spec_id", "workflow_id",
                  "irb_doc_code", "last_modified", "latest_version", "type", "size", "data_store",
                  "document", "user_uid", "url"]
        unknown = INCLUDE
    type = EnumField(FileType)
    url = Method("get_url")

    def get_url(self, obj):
        token = 'not_available'
        if obj.id is None:
            return "" # We can't return a url for a file that isn't stored yet.
        file_url = url_for("/v1_0.crc_api_file_get_file_data_link", file_id=obj.id, _external=True)
        if hasattr(flask.g, 'user'):
            token = flask.g.user.encode_auth_token()
        url = file_url + '?auth_token=' + urllib.parse.quote_plus(token)
        return url


class LookupFileModel(db.Model):
    """Gives us a quick way to tell what kind of lookup is set on a form field.
    Connected to the file data model, so that if a new version of the same file is
    created, we can update the listing."""
    __tablename__ = 'lookup_file'
    id = db.Column(db.Integer, primary_key=True)
    workflow_spec_id = db.Column(db.String)
    task_spec_id = db.Column(db.String)
    field_id = db.Column(db.String)
    is_ldap = db.Column(db.Boolean)  # Allows us to run an ldap query instead of a db lookup.
    file_data_model_id = db.Column(db.Integer, db.ForeignKey('file_data.id'))
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
        model = FileModel
        fields = ["name"]
