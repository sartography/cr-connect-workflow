import jinja2
import marshmallow
from jinja2 import Template
from marshmallow import INCLUDE
from marshmallow_enum import EnumField

from crc import ma
from crc.api.common import ApiError
from crc.models.workflow import WorkflowStatus


class Task(object):
    def __init__(self, id, name, title, type, state, form, documentation, data):
        self.id = id
        self.name = name
        self.title = title
        self.type = type
        self.state = state
        self.form = form
        self.documentation = documentation
        self.data = data

    @classmethod
    def from_spiff(cls, spiff_task):
        documentation = spiff_task.task_spec.documentation if hasattr(spiff_task.task_spec, "documentation") else ""
        instance = cls(spiff_task.id,
                       spiff_task.task_spec.name,
                       spiff_task.task_spec.description,
                       spiff_task.task_spec.__class__.__name__,
                       spiff_task.get_state_name(),
                       None,
                       documentation,
                       spiff_task.data)
        if hasattr(spiff_task.task_spec, "form"):
            instance.form = spiff_task.task_spec.form
        if documentation != "" and documentation is not None:

            instance.process_documentation(documentation)
        return instance

    def process_documentation(self, documentation):
        '''Runs markdown documentation through the Jinja2 processor to inject data
        create loops, etc...'''

        try:
            template = Template(documentation)
            self.documentation = template.render(**self.data)
        except jinja2.exceptions.TemplateError as ue:
            raise ApiError(code="template_error", message="Error processing template for task %s: %s" %
                                                          (self.name, str(ue)), status_code=500)
        # TODO:  Catch additional errors and report back.

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
            "id", "type", "label", "default_value", "options", "validation", "properties", "value"
        ]

    default_value = marshmallow.fields.String(required=False, allow_none=True)
    options = marshmallow.fields.List(marshmallow.fields.Nested(OptionSchema))
    validation = marshmallow.fields.List(marshmallow.fields.Nested(ValidationSchema))
    properties = marshmallow.fields.List(marshmallow.fields.Nested(PropertiesSchema))


class FormSchema(ma.Schema):
    key = marshmallow.fields.String(required=True, allow_none=False)
    fields = marshmallow.fields.List(marshmallow.fields.Nested(FormFieldSchema))


class TaskSchema(ma.Schema):
    class Meta:
        fields = ["id", "name", "title", "type", "state", "form", "documentation", "data"]

    documentation = marshmallow.fields.String(required=False, allow_none=True)
    form = marshmallow.fields.Nested(FormSchema, required=False, allow_none=True)
    title = marshmallow.fields.String(required=False, allow_none=True)

    @marshmallow.post_load
    def make_task(self, data, **kwargs):
        return Task(**data)


class WorkflowApi(object):
    def __init__(self, id, status, user_tasks, last_task, next_task,
                 spec_version, is_latest_spec, workflow_spec_id):
        self.id = id
        self.status = status
        self.user_tasks = user_tasks
        self.last_task = last_task
        self.next_task = next_task
        self.workflow_spec_id = workflow_spec_id
        self.spec_version = spec_version
        self.is_latest_spec = is_latest_spec

class WorkflowApiSchema(ma.Schema):
    class Meta:
        model = WorkflowApi
        fields = ["id", "status", "user_tasks", "last_task", "next_task",
                  "workflow_spec_id", "spec_version", "is_latest_spec"]
        unknown = INCLUDE

    status = EnumField(WorkflowStatus)
    user_tasks = marshmallow.fields.List(marshmallow.fields.Nested(TaskSchema, dump_only=True))
    last_task = marshmallow.fields.Nested(TaskSchema, dump_only=True)
    next_task = marshmallow.fields.Nested(TaskSchema, dump_only=True, required=False)

    @marshmallow.post_load
    def make_workflow(self, data, **kwargs):
        keys = ['id', 'status', 'user_tasks', 'last_task', 'next_task',
                'workflow_spec_id', 'spec_version', 'is_latest_spec']
        filtered_fields = {key: data[key] for key in keys}
        return WorkflowApi(**filtered_fields)
