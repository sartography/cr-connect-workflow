import enum

import marshmallow
from SpiffWorkflow.navigation import NavItem
from marshmallow import INCLUDE
from marshmallow_enum import EnumField

from crc import ma
from crc.models.workflow import WorkflowStatus
from crc.models.file import FileSchema

class MultiInstanceType(enum.Enum):
    none = "none"
    looping = "looping"
    parallel = "parallel"
    sequential = "sequential"


class Task(object):

    ##########################################################################
    #    Custom properties and validations defined in Camunda form fields    #
    ##########################################################################

    # Custom task title
    PROP_EXTENSIONS_TITLE = "display_name"
    PROP_EXTENSIONS_CLEAR_DATA = "clear_data"

    # Field Types
    FIELD_TYPE_STRING = "string"
    FIELD_TYPE_LONG = "long"
    FIELD_TYPE_BOOLEAN = "boolean"
    FIELD_TYPE_DATE = "date"
    FIELD_TYPE_ENUM = "enum"
    FIELD_TYPE_TEXTAREA = "textarea"    # textarea: Multiple lines of text
    FIELD_TYPE_AUTO_COMPLETE = "autocomplete"
    FIELD_TYPE_FILE = "file"
    FIELD_TYPE_FILES = "files"  # files: Multiple files
    FIELD_TYPE_TEL = "tel"  # tel: Phone number
    FIELD_TYPE_EMAIL = "email"  # email: Email address
    FIELD_TYPE_URL = "url"   # url: Website address

    FIELD_PROP_AUTO_COMPLETE_MAX = "autocomplete_num"  # Not used directly, passed in from the front end.

    # Required field
    FIELD_CONSTRAINT_REQUIRED = "required"

    # Field properties and expressions Expressions
    FIELD_PROP_REPEAT = "repeat"
    FIELD_PROP_READ_ONLY = "read_only"
    FIELD_PROP_LDAP_LOOKUP = "ldap.lookup"
    FIELD_PROP_READ_ONLY_EXPRESSION = "read_only_expression"
    FIELD_PROP_HIDE_EXPRESSION = "hide_expression"
    FIELD_PROP_REQUIRED_EXPRESSION = "required_expression"
    FIELD_PROP_LABEL_EXPRESSION = "label_expression"
    FIELD_PROP_REPEAT_HIDE_EXPRESSION = "repeat_hide_expression"
    FIELD_PROP_VALUE_EXPRESSION = "value_expression"

    # Enum field options
    FIELD_PROP_SPREADSHEET_NAME = "spreadsheet.name"
    FIELD_PROP_DATA_NAME = "data.name"
    FIELD_PROP_VALUE_COLUMN = "value.column"
    FIELD_PROP_LABEL_COLUMN = "label.column"

    #FIELD_PROP_SPREADSHEET_VALUE_COLUMN = "spreadsheet.value.column"
    #FIELD_PROP_SPREADSHEET_LABEL_COLUMN = "spreadsheet.label.column"

    # Enum field options values pulled from task data

    # Group and Repeat functions
    FIELD_PROP_GROUP = "group"
    FIELD_PROP_REPLEAT = "repeat"
    FIELD_PROP_REPLEAT_TITLE = "repeat_title"
    FIELD_PROP_REPLEAT_BUTTON = "repeat_button_label"

    # File specific field properties
    FIELD_PROP_DOC_CODE = "doc_code"  # to associate a file upload field with a doc code
    FIELD_PROP_FILE_DATA = "file_data"  # to associate a bit of data with a specific file upload file.

    # Additional properties
    FIELD_PROP_ENUM_TYPE = "enum_type"
    FIELD_PROP_BOOLEAN_TYPE = "boolean_type"
    FIELD_PROP_TEXT_AREA_ROWS = "rows"
    FIELD_PROP_TEXT_AREA_COLS = "cols"
    FIELD_PROP_TEXT_AREA_AUTO = "autosize"
    FIELD_PROP_PLACEHOLDER = "placeholder"
    FIELD_PROP_DESCRIPTION = "description"
    FIELD_PROP_MARKDOWN_DESCRIPTION = "markdown_description"
    FIELD_PROP_HELP = "help"


    ##########################################################################

    def __init__(self, id, name, title, type, state, lane, form, documentation, data,
                 multi_instance_type, multi_instance_count, multi_instance_index,
                 process_name, properties, is_locked=False):
        self.id = id
        self.name = name
        self.title = title
        self.type = type
        self.state = state
        self.form = form
        self.documentation = documentation
        self.data = data
        self.lane = lane
        self.multi_instance_type = multi_instance_type  # Some tasks have a repeat behavior.
        self.multi_instance_count = multi_instance_count  # This is the number of times the task could repeat.
        self.multi_instance_index = multi_instance_index  # And the index of the currently repeating task.
        self.process_name = process_name
        self.properties = properties  # Arbitrary extension properties from BPMN editor.
        self.is_locked = is_locked

    @classmethod
    def valid_property_names(cls):
        return [value for name, value in vars(cls).items() if name.startswith('FIELD_PROP')]

    @classmethod
    def valid_field_types(cls):
        return [value for name, value in vars(cls).items() if name.startswith('FIELD_TYPE')]


class OptionSchema(ma.Schema):
    class Meta:
        fields = ["id", "name", "data"]


class ValidationSchema(ma.Schema):
    class Meta:
        fields = ["name", "config"]


class FormFieldPropertySchema(ma.Schema):
    class Meta:
        fields = ["id", "value"]

class FormFieldSchema(ma.Schema):
    class Meta:
        fields = ["id", "type", "label", "default_value", "options", "validation", "properties", "value"]

    default_value = marshmallow.fields.String(required=False, allow_none=True)
    options = marshmallow.fields.List(marshmallow.fields.Nested(OptionSchema))
    validation = marshmallow.fields.List(marshmallow.fields.Nested(ValidationSchema))
    properties = marshmallow.fields.List(marshmallow.fields.Nested(FormFieldPropertySchema))


class FormSchema(ma.Schema):
    key = marshmallow.fields.String(required=True, allow_none=False)
    fields = marshmallow.fields.List(marshmallow.fields.Nested(FormFieldSchema))


class TaskSchema(ma.Schema):
    class Meta:
        fields = ["id", "name", "title", "type", "state", "lane", "form", "documentation", "data", "multi_instance_type",
                  "multi_instance_count", "multi_instance_index", "process_name", "properties"]

    multi_instance_type = EnumField(MultiInstanceType)
    documentation = marshmallow.fields.String(required=False, allow_none=True)
    form = marshmallow.fields.Nested(FormSchema, required=False, allow_none=True)
    title = marshmallow.fields.String(required=False, allow_none=True)
    process_name = marshmallow.fields.String(required=False, allow_none=True)
    lane = marshmallow.fields.String(required=False, allow_none=True)

    @marshmallow.post_load
    def make_task(self, data, **kwargs):
        return Task(**data)


class NavigationItemSchema(ma.Schema):
    class Meta:
        fields = ["spec_id", "name", "spec_type", "task_id", "description", "backtracks", "indent",
                  "lane", "state", "children"]
        unknown = INCLUDE
    state = marshmallow.fields.String(required=False, allow_none=True)
    description = marshmallow.fields.String(required=False, allow_none=True)
    backtracks = marshmallow.fields.String(required=False, allow_none=True)
    lane = marshmallow.fields.String(required=False, allow_none=True)
    task_id = marshmallow.fields.String(required=False, allow_none=True)
    children = marshmallow.fields.List(marshmallow.fields.Nested(lambda: NavigationItemSchema()))

    @marshmallow.post_load
    def make_nav(self, data, **kwargs):
        state = data.pop('state', None)
        task_id = data.pop('task_id', None)
        children = data.pop('children', [])
        spec_type = data.pop('spec_type', None)
        item = NavItem(**data)
        item.state = state
        item.task_id = task_id
        item.children = children
        item.spec_type = spec_type
        return item

class DocumentDirectorySchema(ma.Schema):
    level = marshmallow.fields.String()
    file = marshmallow.fields.Nested(FileSchema)
    filecount = marshmallow.fields.Integer()
    expanded = marshmallow.fields.Boolean()
    children = marshmallow.fields.Nested("self",many=True)


class DocumentDirectory(object):
    def __init__(self, level=None, file=None, children=None):

        self.level = level
        self.file = file
        self.expanded = False
        self.filecount = 0
        if children is None:
            self.children = list()
        else:
            self.children=children


class WorkflowApi(object):
    def __init__(self, id, status, next_task, navigation,
                 workflow_spec_id, total_tasks, completed_tasks,
                 last_updated, is_review, title, study_id, state):
        self.id = id
        self.status = status
        self.next_task = next_task  # The next task that requires user input.
        self.navigation = navigation
        self.workflow_spec_id = workflow_spec_id
        self.total_tasks = total_tasks
        self.completed_tasks = completed_tasks
        self.last_updated = last_updated
        self.title = title
        self.is_review = is_review
        self.study_id = study_id or ''
        self.state = state


class WorkflowApiSchema(ma.Schema):
    class Meta:
        model = WorkflowApi
        fields = ["id", "status", "next_task", "navigation",
                  "workflow_spec_id", "total_tasks", "completed_tasks",
                  "last_updated", "is_review", "title", "study_id", "state"]
        unknown = INCLUDE

    status = EnumField(WorkflowStatus)
    next_task = marshmallow.fields.Nested(TaskSchema, dump_only=True, required=False)
    navigation = marshmallow.fields.List(marshmallow.fields.Nested(NavigationItemSchema, dump_only=True))
    state = marshmallow.fields.Mapping(data_key="state", allow_none=True)

    @marshmallow.post_load
    def make_workflow(self, data, **kwargs):
        keys = ['id', 'status', 'next_task', 'navigation',
                'workflow_spec_id', "total_tasks", "completed_tasks",
                "last_updated", "is_review", "title", "study_id", "state"]
        filtered_fields = {key: data[key] for key in keys}
        filtered_fields['next_task'] = TaskSchema().make_task(data['next_task'])
        return WorkflowApi(**filtered_fields)
