import enum

import marshmallow
from marshmallow import INCLUDE
from marshmallow_enum import EnumField

from crc import ma
from crc.models.workflow import WorkflowStatus


class MultiInstanceType(enum.Enum):
    none = "none"
    looping = "looping"
    parallel = "parallel"
    sequential = "sequential"


class NavigationItem(object):
    def __init__(self, id, task_id, name, title, backtracks, level, indent, child_count, state, is_decision,
                 task=None, lane=None):
        self.id = id
        self.task_id = task_id
        self.name = name,
        self.title = title
        self.backtracks = backtracks
        self.level = level
        self.indent = indent
        self.child_count = child_count
        self.state = state
        self.is_decision = is_decision
        self.task = task

class Task(object):

    PROP_OPTIONS_REPEAT = "repeat"
    PROP_OPTIONS_FILE = "spreadsheet.name"
    PROP_OPTIONS_VALUE_COLUMN = "spreadsheet.value.column"
    PROP_OPTIONS_LABEL_COL = "spreadsheet.label.column"
    PROP_OPTIONS_READ_ONLY = "read_only"
    PROP_LDAP_LOOKUP = "ldap.lookup"
    VALIDATION_REQUIRED = "required"
    FIELD_TYPE_AUTO_COMPLETE = "autocomplete"


    def __init__(self, id, name, title, type, state, form, documentation, data,
                 multi_instance_type, multi_instance_count, multi_instance_index, process_name, properties):
        self.id = id
        self.name = name
        self.title = title
        self.type = type
        self.state = state
        self.form = form
        self.documentation = documentation
        self.data = data
        self.multi_instance_type = multi_instance_type  # Some tasks have a repeat behavior.
        self.multi_instance_count = multi_instance_count  # This is the number of times the task could repeat.
        self.multi_instance_index = multi_instance_index  # And the index of the currently repeating task.
        self.process_name = process_name
        self.properties = properties  # Arbitrary extension properties from BPMN editor.


class OptionSchema(ma.Schema):
    class Meta:
        fields = ["id", "name"]


class ValidationSchema(ma.Schema):
    class Meta:
        fields = ["name", "config"]


class FormFieldPropertySchema(ma.Schema):
    class Meta:
        fields = [
            "id", "value"
        ]

class FormFieldSchema(ma.Schema):
    class Meta:
        fields = [
            "id", "type", "label", "default_value", "options", "validation", "properties", "value"
        ]

    default_value = marshmallow.fields.String(required=False, allow_none=True)
    options = marshmallow.fields.List(marshmallow.fields.Nested(OptionSchema))
    validation = marshmallow.fields.List(marshmallow.fields.Nested(ValidationSchema))
    properties = marshmallow.fields.List(marshmallow.fields.Nested(FormFieldPropertySchema))


class FormSchema(ma.Schema):
    key = marshmallow.fields.String(required=True, allow_none=False)
    fields = marshmallow.fields.List(marshmallow.fields.Nested(FormFieldSchema))


class TaskSchema(ma.Schema):
    class Meta:
        fields = ["id", "name", "title", "type", "state", "form", "documentation", "data", "multi_instance_type",
                  "multi_instance_count", "multi_instance_index", "process_name", "properties"]

    multi_instance_type = EnumField(MultiInstanceType)
    documentation = marshmallow.fields.String(required=False, allow_none=True)
    form = marshmallow.fields.Nested(FormSchema, required=False, allow_none=True)
    title = marshmallow.fields.String(required=False, allow_none=True)
    process_name = marshmallow.fields.String(required=False, allow_none=True)

    @marshmallow.post_load
    def make_task(self, data, **kwargs):
        return Task(**data)


class NavigationItemSchema(ma.Schema):
    class Meta:
        fields = ["id", "task_id", "name", "title", "backtracks", "level", "indent", "child_count", "state",
                  "is_decision", "task"]
        unknown = INCLUDE
    task = marshmallow.fields.Nested(TaskSchema, dump_only=True, required=False, allow_none=True)
    backtracks = marshmallow.fields.String(required=False, allow_none=True)
    title = marshmallow.fields.String(required=False, allow_none=True)
    task_id = marshmallow.fields.String(required=False, allow_none=True)


class WorkflowApi(object):
    def __init__(self, id, status, next_task, navigation,
                 spec_version, is_latest_spec, workflow_spec_id, total_tasks, completed_tasks, last_updated, title):
        self.id = id
        self.status = status
        self.next_task = next_task  # The next task that requires user input.
        self.navigation = navigation
        self.workflow_spec_id = workflow_spec_id
        self.spec_version = spec_version
        self.is_latest_spec = is_latest_spec
        self.total_tasks = total_tasks
        self.completed_tasks = completed_tasks
        self.last_updated = last_updated
        self.title = title

class WorkflowApiSchema(ma.Schema):
    class Meta:
        model = WorkflowApi
        fields = ["id", "status", "next_task", "navigation",
                  "workflow_spec_id", "spec_version", "is_latest_spec", "total_tasks", "completed_tasks",
                  "last_updated", "title"]
        unknown = INCLUDE

    status = EnumField(WorkflowStatus)
    next_task = marshmallow.fields.Nested(TaskSchema, dump_only=True, required=False)
    navigation = marshmallow.fields.List(marshmallow.fields.Nested(NavigationItemSchema, dump_only=True))

    @marshmallow.post_load
    def make_workflow(self, data, **kwargs):
        keys = ['id', 'status', 'next_task', 'navigation',
                'workflow_spec_id', 'spec_version', 'is_latest_spec', "total_tasks", "completed_tasks",
                "last_updated", "title"]
        filtered_fields = {key: data[key] for key in keys}
        filtered_fields['next_task'] = TaskSchema().make_task(data['next_task'])
        return WorkflowApi(**filtered_fields)
