import enum

from SpiffWorkflow import Task
from flask_marshmallow.sqla import ModelSchema
from marshmallow import post_load, fields
from marshmallow_enum import EnumField
from sqlalchemy import func

from crc import db, ma


class ProtocolBuilderStatus(enum.Enum):
    out_of_date = "out_of_date"
    in_process = "in_process"
    complete = "complete"
    updating = "updating"


class StudyModel(db.Model):
    __tablename__ = 'study'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    last_updated = db.Column(db.DateTime(timezone=True), default=func.now())
    protocol_builder_status = db.Column(db.Enum(ProtocolBuilderStatus))
    primary_investigator_id = db.Column(db.String)
    sponsor = db.Column(db.String)
    ind_number = db.Column(db.String)


class StudySchema(ModelSchema):
    class Meta:
        model = StudyModel

    protocol_builder_status = EnumField(ProtocolBuilderStatus)


class WorkflowSpecModel(db.Model):
    __tablename__ = 'workflow_spec'
    id = db.Column(db.String, primary_key=True)
    display_name = db.Column(db.String)
    description = db.Column(db.Text)


class WorkflowSpecSchema(ModelSchema):
    class Meta:
        model = WorkflowSpecModel


class FileType(enum.Enum):
    bpmn = "bpmm"
    svg = "svg"
    dmn = "dmn"


class FileDataModel(db.Model):
    __tablename__ = 'file_data'
    id = db.Column(db.Integer, db.ForeignKey('file.id'), primary_key=True)
    data = db.Column(db.LargeBinary)
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


class WorkflowStatus(enum.Enum):
    new = "new"
    user_input_required = "user_input_required"
    waiting = "waiting"
    complete = "complete"


class WorkflowModel(db.Model):
    __tablename__ = 'workflow'
    id = db.Column(db.Integer, primary_key=True)
    bpmn_workflow_json = db.Column(db.TEXT)
    status = db.Column(db.Enum(WorkflowStatus))
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'))
    workflow_spec_id = db.Column(db.Integer, db.ForeignKey('workflow_spec.id'))


class WorkflowSchema(ModelSchema):
    class Meta:
        model = WorkflowModel

    status = EnumField(WorkflowStatus)


class Task:
    def __init__(self, id, name, title, type, state, form, documentation):
        self.id = id
        self.name = name
        self.title = title
        self.type = type
        self.state = state
        self.form = form
        self.documentation = documentation

    @classmethod
    def from_spiff(cls, spiff_task):
        instance = cls(spiff_task.id,
                       spiff_task.task_spec.name,
                       spiff_task.task_spec.description,
                       spiff_task.get_state_name(),
                       "task",
                       {},
                       spiff_task.task_spec.documentation)
        if hasattr(spiff_task.task_spec, "form"):
            instance.type = "form"
            instance.form = spiff_task.task_spec.form
        return instance


class OptionSchema(ma.Schema):
    class Meta:
        fields = ["id", "name"]


class ValidationSchema(ma.Schema):
    class Meta:
        fields = ["name", "config"]


class PropertiesSchema(ma.Schema):
    class Meta:
        fields = ["id", "value"]


class FieldSchema(ma.Schema):
    class Meta:
        fields = [
            "id", "type", "label", "defaultValue", "options", "validation", "properties"
        ]

    options = fields.List(fields.Nested(OptionSchema))
    validation = fields.List(fields.Nested(ValidationSchema))
    properties = fields.List(fields.Nested(PropertiesSchema))


class FormSchema(ma.Schema):
    class Meta:
        fields = ["key", "fields"]

    fields = fields.List(fields.Nested(FieldSchema))


class TaskSchema(ma.Schema):
    class Meta:
        fields = ["id", "name", "title", "type", "state", "form", "documentation"]

    form = fields.Nested(FormSchema)

    @post_load
    def make_task(self, data, **kwargs):
        return Task(**data)
