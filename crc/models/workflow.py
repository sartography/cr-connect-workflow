import enum

import marshmallow
from marshmallow_enum import EnumField
from marshmallow_sqlalchemy import ModelSchema

from crc import db, ma


class WorkflowSpecModel(db.Model):
    __tablename__ = 'workflow_spec'
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    display_name = db.Column(db.String)
    description = db.Column(db.Text)
    primary_process_id = db.Column(db.String)


class WorkflowSpecModelSchema(ModelSchema):
    class Meta:
        model = WorkflowSpecModel


class WorkflowStatus(enum.Enum):
    new = "new"
    user_input_required = "user_input_required"
    waiting = "waiting"
    complete = "complete"


class WorkflowModel(db.Model):
    __tablename__ = 'workflow'
    id = db.Column(db.Integer, primary_key=True)
    bpmn_workflow_json = db.Column(db.JSON)
    status = db.Column(db.Enum(WorkflowStatus))
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'))
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'))


class WorkflowModelSchema(ModelSchema):
    class Meta:
        model = WorkflowModel
        include_fk = True  # Includes foreign keys

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


class FormFieldSchema(ma.Schema):
    class Meta:
        fields = [
            "id", "type", "label", "defaultValue", "options", "validation", "properties", "value"
        ]

    options = marshmallow.fields.List(marshmallow.fields.Nested(OptionSchema))
    validation = marshmallow.fields.List(marshmallow.fields.Nested(ValidationSchema))
    properties = marshmallow.fields.List(marshmallow.fields.Nested(PropertiesSchema))


class FormSchema(ma.Schema):
    key = marshmallow.fields.String(required=True, allow_none=False)
    fields = marshmallow.fields.List(marshmallow.fields.Nested(FormFieldSchema))


class TaskSchema(ma.Schema):
    class Meta:
        fields = ["id", "name", "title", "type", "state", "form", "documentation"]

    documentation = marshmallow.fields.String(required=False, allow_none=True)
    form = marshmallow.fields.Nested(FormSchema)

    @marshmallow.post_load
    def make_task(self, data, **kwargs):
        return Task(**data)
