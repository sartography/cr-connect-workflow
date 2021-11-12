from crc import db
from crc.api.common import ApiError
from crc.models.api_models import Task
from crc.models.workflow import WorkflowModel
from crc.scripts.script import Script
from crc.services.lookup_service import LookupService
from crc.services.workflow_processor import WorkflowProcessor


class EnumLabel(Script):

    UNKNOWN = "unknown"

    def get_description(self):
        return """In a form, when doing a select list, multi-select, autocomplete, etc... you are left with a single
        value.  You may want to know the label that was displayed to the user as well.  This will return the label, given
        enough information to do so, which requires the name of the user task, the name of the form field, and the value
        of the selected item. 

Example:
pet_label = enum_label('task_pet_form', 'pet', '1')    // might return 'Dog' which has the value of 1
alternately, you can use named parameters:
pet_label = enum_label(task='task_pet_form',field='pet',value='1')    // might return 'Dog' which has the value of 1
"""

    def do_task_validate_only(self, spiff_task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(spiff_task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, spiff_task, study_id, workflow_id, *args, **kwargs):

        task_name, field_name, value = self.validate_arguments(*args, **kwargs)

        # get the field information for the provided task_name (NOT the current task)
        workflow_model = db.session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        field = self.find_field(task_name, field_name, spiff_task.workflow)
        print(field)

        if field.type == Task.FIELD_TYPE_AUTO_COMPLETE:
            return self.autocomplete_label(workflow_model, task_name, field, value)
        elif field.type == Task.FIELD_TYPE_ENUM and hasattr(field, 'options'):
            return self.enum_with_options_label(field, value)
        elif field.has_property(Task.FIELD_PROP_DATA_NAME):
            return self.enum_from_task_data_label(spiff_task, field, value)

    def find_field(self, task_name, field_name, workflow):
        for spec in workflow.spec.task_specs.values():
            if spec.name == task_name:
                for field in spec.form.fields:
                    if field.id == field_name:
                        return field
                raise ApiError("invalid_field",
                               f"The task '{task_name}' has no field named '{field_name}'")
        raise ApiError("invalid_spec",
                   f"Unable to find a task in the workflow called '{task_name}'")


    def autocomplete_label(self, workflow_model, task_name, field, value):
        label_column = field.get_property(Task.FIELD_PROP_LABEL_COLUMN)
        result = LookupService().lookup(workflow_model, task_name, field.id, '', value=value, limit=1)
        if len(result) > 0:
            return result[0][label_column]
        else:
            return self.UNKNOWN

    def enum_with_options_label(self, field, value):
        for option in field.options:
            if option.id == value:
                return option.name
        return self.UNKNOWN

    def enum_from_task_data_label(self, task, field, value):
        data_name = field.get_property(Task.FIELD_PROP_DATA_NAME)
        value_column = field.get_property(Task.FIELD_PROP_VALUE_COLUMN)
        label_column = field.get_property(Task.FIELD_PROP_LABEL_COLUMN)
        if data_name in task.data:
            for d in task.data[data_name]:
                if d[value_column] == value:
                    return d[label_column]
        return self.UNKNOWN

    def validate_arguments(self, *args, **kwargs):
        if len(args) != 3 and len(kwargs) != 3:
            raise ApiError(code="invalid_argument",
                           message="enum_label requires three arguments: Task id, Field id, and the selected value.")
        elif len(args) == 3:
            return args
        else:
            if not 'task' in kwargs:
                raise ApiError(code="invalid_argument",
                               message="you must specify the 'task_name', that is the name of the task with a form and field")
            if not 'field' in kwargs:
                raise ApiError(code="invalid_argument",
                               message="you must specify the 'field', that is the name of the field with an enum.")
            if not 'value' in kwargs:
                raise ApiError(code="invalid_argument",
                               message="you must specify the 'value', that is the value of the enum you wish to get a label for.")
            return kwargs['task'], kwargs['field'], kwargs['value']

