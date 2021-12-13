import copy
import json
import sys
import traceback
import random
import string
from datetime import datetime
from typing import List

import jinja2
from SpiffWorkflow import Task as SpiffTask, WorkflowException, NavItem
from SpiffWorkflow.bpmn.PythonScriptEngine import Box
from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent
from SpiffWorkflow.bpmn.specs.ManualTask import ManualTask
from SpiffWorkflow.bpmn.specs.ScriptTask import ScriptTask
from SpiffWorkflow.bpmn.specs.StartEvent import StartEvent
from SpiffWorkflow.bpmn.specs.UserTask import UserTask
from SpiffWorkflow.dmn.specs.BusinessRuleTask import BusinessRuleTask
from SpiffWorkflow.specs import CancelTask, StartTask
from SpiffWorkflow.util.deep_merge import DeepMerge
from SpiffWorkflow.util.metrics import timeit

from crc import db, app, session
from crc.api.common import ApiError
from crc.models.api_models import Task, MultiInstanceType, WorkflowApi
from crc.models.file import LookupDataModel, FileModel, File, FileSchema
from crc.models.ldap import LdapModel
from crc.models.study import StudyModel
from crc.models.task_event import TaskEventModel
from crc.models.user import UserModel
from crc.models.workflow import WorkflowModel, WorkflowStatus, WorkflowSpecModel, WorkflowSpecCategoryModel
from crc.services.data_store_service import DataStoreBase

from crc.services.document_service import DocumentService
from crc.services.file_service import FileService
from crc.services.jinja_service import JinjaService
from crc.services.lookup_service import LookupService
from crc.services.study_service import StudyService
from crc.services.user_service import UserService
from crc.services.workflow_processor import WorkflowProcessor


class WorkflowService(object):
    TASK_ACTION_COMPLETE = "COMPLETE"
    TASK_ACTION_TOKEN_RESET = "TOKEN_RESET"
    TASK_ACTION_HARD_RESET = "HARD_RESET"
    TASK_ACTION_SOFT_RESET = "SOFT_RESET"
    TASK_ACTION_ASSIGNMENT = "ASSIGNMENT"  # Whenever the lane changes between tasks we assign the task to specifc user.

    TASK_STATE_LOCKED = "LOCKED" # When the task belongs to a different user.

    """Provides tools for processing workflows and tasks.  This
     should at some point, be the only way to work with Workflows, and
     the workflow Processor should be hidden behind this service.
     This will help maintain a structure that avoids circular dependencies.
     But for now, this contains tools for converting spiff-workflow models into our
     own API models with additional information and capabilities and
     handles the testing of a workflow specification by completing it with
     random selections, attempting to mimic a front end as much as possible. """

    from crc.services.user_service import UserService
    @staticmethod
    def make_test_workflow(spec_id, validate_study_id=None):
        try:
            user = UserService.current_user()
        except ApiError as e:
            user = None
        if not user:
            user = db.session.query(UserModel).filter_by(uid="test").first()
        if not user:
            db.session.add(LdapModel(uid="test"))
            db.session.add(UserModel(uid="test"))
            db.session.commit()
            user = db.session.query(UserModel).filter_by(uid="test").first()
        if validate_study_id:
            study = db.session.query(StudyModel).filter_by(id=validate_study_id).first()
        else:
            study = db.session.query(StudyModel).filter_by(user_uid=user.uid).first()
        if not study:
            db.session.add(StudyModel(user_uid=user.uid, title="test"))
            db.session.commit()
            study = db.session.query(StudyModel).filter_by(user_uid=user.uid).first()
        workflow_model = WorkflowModel(status=WorkflowStatus.not_started,
                                       workflow_spec_id=spec_id,
                                       last_updated=datetime.utcnow(),
                                       study=study)
        return workflow_model

    @staticmethod
    def delete_test_data(workflow: WorkflowModel):
        db.session.delete(workflow)
        # Also, delete any test study or user models that may have been created.
        for study in db.session.query(StudyModel).filter(StudyModel.user_uid == "test"):
            StudyService.delete_study(study.id)
        user = db.session.query(UserModel).filter_by(uid="test").first()
        ldap = db.session.query(LdapModel).filter_by(uid="test").first()
        if ldap:
            db.session.delete(ldap)
        if user:
            db.session.delete(user)
        db.session.commit()

    @staticmethod
    def do_waiting():
        records = db.session.query(WorkflowModel).filter(WorkflowModel.status==WorkflowStatus.waiting).all()
        for workflow_model in records:
            try:
                app.logger.info('Processing workflow %s' % workflow_model.id)
                processor = WorkflowProcessor(workflow_model)
                processor.bpmn_workflow.refresh_waiting_tasks()
                processor.bpmn_workflow.do_engine_steps()
                processor.save()
            except Exception as e:
                workflow_model.status = WorkflowStatus.erroring
                app.logger.error(f"Error running waiting task for workflow #%i (%s) for study #%i.  %s" %
                                 (workflow_model.id,
                                  workflow_model.workflow_spec.id,
                                  workflow_model.study_id,
                                  str(e)))

    @staticmethod
    def raise_if_disabled(spec_id, study_id):
        """Raise an exception of the workflow is not enabled and can not be executed."""
        if study_id is not None:
            study_model = session.query(StudyModel).filter(StudyModel.id == study_id).first()
            spec_model = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id == spec_id).first()
            status = StudyService._get_study_status(study_model)
            if spec_model.id in status and status[spec_model.id]['status'] == 'disabled':
                raise ApiError(code='disabled_workflow', message=f"This workflow is disabled. {status[spec_model.id]['message']}")

    @staticmethod
    @timeit
    def test_spec(spec_id, validate_study_id=None, test_until=None, required_only=False):
        """Runs a spec through it's paces to see if it results in any errors.
          Not fool-proof, but a good sanity check.  Returns the final data
          output form the last task if successful.

          test_until - stop running the validation when you reach this task spec.

          required_only can be set to true, in which case this will run the
          spec, only completing the required fields, rather than everything.
          """

        workflow_model = WorkflowService.make_test_workflow(spec_id, validate_study_id)
        try:
            processor = WorkflowProcessor(workflow_model, validate_only=True)
            count = 0

            while not processor.bpmn_workflow.is_completed():
                    processor.bpmn_workflow.get_deep_nav_list()  # Assure no errors with navigation.
                    exit_task = processor.bpmn_workflow.do_engine_steps(exit_at=test_until) 
                    if (exit_task != None):
                            raise ApiError.from_task("validation_break",
                                        f"The validation has been exited early on task '{exit_task.task_spec.id}' and was parented by ",
                                        exit_task.parent)
                    tasks = processor.bpmn_workflow.get_tasks(SpiffTask.READY)
                    for task in tasks:
                        if task.task_spec.lane is not None and task.task_spec.lane not in task.data:
                            raise ApiError.from_task("invalid_role",
                                        f"This task is in a lane called '{task.task_spec.lane}', The "
                                        f" current task data must have information mapping this role to "
                                        f" a unique user id.", task)
                        task_api = WorkflowService.spiff_task_to_api_task(
                            task,
                            add_docs_and_forms=True)  # Assure we try to process the documentation, and raise those errors.
                        # make sure forms have a form key
                        if hasattr(task_api, 'form') and task_api.form is not None and task_api.form.key == '':
                            raise ApiError(code='missing_form_key',
                                        message='Forms must include a Form Key.',
                                        task_id=task.id,
                                        task_name=task.get_name())
                        WorkflowService.populate_form_with_random_data(task, task_api, required_only)
                        processor.complete_task(task)
                        if test_until == task.task_spec.name:
                            raise ApiError.from_task(
                                "validation_break",
                                f"The validation has been exited early on task '{task.task_spec.name}' "
                                f"and was parented by ",
                                task.parent)
                    count += 1
                    if count >= 100:
                        raise ApiError(code='unending_validation',
                                       message=f'There appears to be no way to complete this workflow,'
                                               f' halting validation.')

            WorkflowService._process_documentation(processor.bpmn_workflow.last_task.parent.parent)

        except WorkflowException as we:
            raise ApiError.from_workflow_exception("workflow_validation_exception", str(we), we)
        finally:
            WorkflowService.delete_test_data(workflow_model)
        return processor.bpmn_workflow.last_task.data

    @staticmethod
    def populate_form_with_random_data(task, task_api, required_only):
        """populates a task with random data - useful for testing a spec."""

        if not hasattr(task.task_spec, 'form'): return

        # Here we serialize and deserialize the task data, just as we would if sending it to the front end.
        data = json.loads(app.json_encoder().encode(o=task_api.data))

        # Just like with the front end, we start with what was already there, and modify it.
        form_data = data

        hide_groups = []
        for field in task_api.form.fields:
            # Assure we have a field type
            if field.type is None:
                raise ApiError(code='invalid_form_data',
                                message = f'Type is missing for field "{field.id}". A field type must be provided.',
                                task_id = task.id,
                                task_name = task.get_name())
                # Assure we have valid ids
            if not WorkflowService.check_field_id(field.id):
                raise ApiError(code='invalid_form_id',
                               message=f'Invalid Field name: "{field.id}".  A field ID must begin with a letter, '
                                       f'and can only contain letters, numbers, and "_"',
                               task_id = task.id,
                               task_name = task.get_name())
            # Assure field has valid properties
            WorkflowService.check_field_properties(field, task)
            WorkflowService.check_field_type(field, task)

            # Process the label of the field if it is dynamic.
            if field.has_property(Task.FIELD_PROP_LABEL_EXPRESSION):
                result = WorkflowService.evaluate_property(Task.FIELD_PROP_LABEL_EXPRESSION, field, task)
                field.label = result

            # If a field is hidden and required, it must have a default value or value_expression
            if field.has_property(Task.FIELD_PROP_HIDE_EXPRESSION) and field.has_validation(Task.FIELD_CONSTRAINT_REQUIRED):
                if not field.has_property(Task.FIELD_PROP_VALUE_EXPRESSION) and \
                        (not (hasattr(field, 'default_value')) or field.default_value is None):
                    raise ApiError(code='hidden and required field missing default',
                                   message=f'Field "{field.id}" is required but can be hidden. It must have either a default value or a value_expression',
                                   task_id='task.id',
                                   task_name=task.get_name())

            # If the field is hidden and not required, it should not produce a value.
            if field.has_property(Task.FIELD_PROP_HIDE_EXPRESSION) and not field.has_validation(Task.FIELD_CONSTRAINT_REQUIRED):
                if WorkflowService.evaluate_property(Task.FIELD_PROP_HIDE_EXPRESSION, field, task):
                    continue

            # A task should only have default_value **or** value expression, not both.
            if field.has_property(Task.FIELD_PROP_VALUE_EXPRESSION) and (hasattr(field, 'default_value') and field.default_value):
                raise ApiError.from_task(code='default value and value_expression',
                                         message=f'This task ({task.get_name()}) has both a default_value and value_expression. Please fix this to only have one or the other.',
                                         task=task)
            # If we have a default_value or value_expression, try to set the default
            if field.has_property(Task.FIELD_PROP_VALUE_EXPRESSION) or (hasattr(field, 'default_value') and field.default_value):
                form_data[field.id] = WorkflowService.get_default_value(field, task)
                if not field.has_property(Task.FIELD_PROP_REPEAT):
                    continue

            # If we are only populating required fields, and this isn't required. stop here.
            if required_only:
                if (not field.has_validation(Task.FIELD_CONSTRAINT_REQUIRED) or
                        field.get_validation(Task.FIELD_CONSTRAINT_REQUIRED).lower().strip() != "true"):
                    continue # Don't include any fields that aren't specifically marked as required.
                if field.has_property(Task.FIELD_PROP_REQUIRED_EXPRESSION):
                    result = WorkflowService.evaluate_property(Task.FIELD_PROP_REQUIRED_EXPRESSION, field, task)
                    if not result and required_only:
                        continue # Don't complete fields that are not required.

            # If it is read only, stop here.
            if field.has_property("read_only") and field.get_property(Task.FIELD_PROP_READ_ONLY).lower().strip() == "true":
                continue # Don't mess about with read only fields.

            if field.has_property(Task.FIELD_PROP_REPEAT) and field.has_property(Task.FIELD_PROP_GROUP):
                raise ApiError.from_task("group_repeat", f'Fields cannot have both group and repeat properties. '
                                                         f' Please remove one of these properties. ',
                                         task=task)

            if field.has_property(Task.FIELD_PROP_REPEAT):
                group = field.get_property(Task.FIELD_PROP_REPEAT)
                if group in form_data and not(isinstance(form_data[group], list)):
                    raise ApiError.from_task("invalid_group",
                                             f'You are grouping form fields inside a variable that is defined '
                                             f'elsewhere: {group}.  Be sure that you use a unique name for the '
                                             f'for repeat and group expressions that is not also used for a field name.'
                                             , task=task)
                if field.has_property(Task.FIELD_PROP_REPEAT_HIDE_EXPRESSION):
                    result = WorkflowService.evaluate_property(Task.FIELD_PROP_REPEAT_HIDE_EXPRESSION, field, task)
                    if not result:
                        hide_groups.append(group)
                if group not in form_data and group not in hide_groups:
                    form_data[group] = [{},{},{}]
                if group in form_data and group not in hide_groups:
                    for i in range(3):
                        form_data[group][i][field.id] = WorkflowService.get_random_data_for_field(field, task)
            else:
                form_data[field.id] = WorkflowService.get_random_data_for_field(field, task)
        if task.data is None:
            task.data = {}

        # jsonify, and de-jsonify the data to mimic how data will be returned from the front end for forms and assures
        # we aren't generating something that can't be serialized.
        try:
            form_data_string = app.json_encoder().encode(o=form_data)
        except TypeError as te:
            raise ApiError.from_task(code='serialize_error',
                                     message=f'Something cannot be serialized. Message is: {te}',
                                     task=task)
        extracted_form_data = WorkflowService().extract_form_data(json.loads(form_data_string), task)
        task.update_data(extracted_form_data)

    @staticmethod
    def check_field_id(id):
        """Assures that field names are valid Python and Javascript names."""
        if not id[0].isalpha():
            return False
        for char in id[1:len(id)]:
            if char.isalnum() or char == '_' or char == '.':
                pass
            else:
                return False
        return True

    @staticmethod
    def check_field_properties(field, task):
        """Assures that all properties are valid on a given workflow."""
        field_prop_names = list(map(lambda fp: fp.id, field.properties))
        valid_names = Task.valid_property_names()
        for name in field_prop_names:
            if name not in valid_names:
                raise ApiError.from_task("invalid_field_property",
                                         f'The field {field.id} contains an unsupported '
                                         f'property: {name}', task=task)

    @staticmethod
    def check_field_type(field, task):
        """Assures that the field type is valid."""
        valid_types = Task.valid_field_types()
        if field.type not in valid_types:
            raise ApiError.from_task("invalid_field_type",
                                     f'The field {field.id} has an unknown field type '
                                     f'{field.type}, valid types include {valid_types}', task=task)

    @staticmethod
    def post_process_form(task):
        """Looks through the fields in a submitted form, acting on any properties."""
        if not hasattr(task.task_spec, 'form'): return
        for field in task.task_spec.form.fields:
            data = task.data
            # If we have a repeat field, make sure it is used before processing it
            if field.has_property(Task.FIELD_PROP_REPEAT) and field.get_property(Task.FIELD_PROP_REPEAT) in task.data.keys():
                repeat_array = task.data[field.get_property(Task.FIELD_PROP_REPEAT)]
                for repeat_data in repeat_array:
                    WorkflowService.__post_process_field(task, field, repeat_data)
            else:
                WorkflowService.__post_process_field(task, field, data)

    @staticmethod
    def __post_process_field(task, field, data):
        if field.has_property(Task.FIELD_PROP_DOC_CODE) and field.id in data:
            # This is generally handled by the front end, but it is possible that the file was uploaded BEFORE
            # the doc_code was correctly set, so this is a stop gap measure to assure we still hit it correctly.
            file_id = data[field.id]["id"]
            doc_code = task.workflow.script_engine._evaluate(field.get_property(Task.FIELD_PROP_DOC_CODE), **data)
            file = db.session.query(FileModel).filter(FileModel.id == file_id).first()
            if(file):
                file.irb_doc_code = doc_code
                db.session.commit()
            else:
                # We have a problem, the file doesn't exist, and was removed, but it is still referenced in the data
                # At least attempt to clear out the data.
                data = {}
        if field.has_property(Task.FIELD_PROP_FILE_DATA) and \
                field.get_property(Task.FIELD_PROP_FILE_DATA) in data and \
                field.id in data and data[field.id]:
            file_id = data[field.get_property(Task.FIELD_PROP_FILE_DATA)]["id"]
            data_args = (field.id, data[field.id])
            DataStoreBase().set_data_common(task.id, None, None, None, None, None, file_id, *data_args)

    @staticmethod
    def evaluate_property(property_name, field, task):
        expression = field.get_property(property_name)

        data = task.data
        if field.has_property(Task.FIELD_PROP_REPEAT):
            # Then you must evaluate the expression based on the data within the group, if that data exists.
            # There may not be data available in the group, if no groups where added
            group = field.get_property(Task.FIELD_PROP_REPEAT)
            if group in task.data and len(task.data[group]) > 0:
                # Here we must make the current group data top level (as it would be in a repeat section) but
                # make all other top level task data available as well.
                new_data = copy.deepcopy(task.data)
                del(new_data[group])
                data = task.data[group][0]
                data.update(new_data)
            else:
                return None  # We may not have enough information to process this

        try:
            return task.workflow.script_engine._evaluate(expression, **data)
        except Exception as e:
            message = f"The field {field.id} contains an invalid expression. {e}"
            raise ApiError.from_task(f'invalid_{property_name}', message, task=task)

    @staticmethod
    def has_lookup(field):
        """Returns true if this is a lookup field."""
        """Note, this does not include enums based on task data, that
        is populated when the form is created, not as a lookup from a data table. """
        has_ldap_lookup = field.has_property(Task.FIELD_PROP_LDAP_LOOKUP)
        has_file_lookup = field.has_property(Task.FIELD_PROP_SPREADSHEET_NAME)
        return has_ldap_lookup or has_file_lookup


    @staticmethod
    def get_default_value(field, task):
        has_lookup = WorkflowService.has_lookup(field)

        default = field.default_value
        # If there is a value expression, use that rather than the default value.
        if field.has_property(Task.FIELD_PROP_VALUE_EXPRESSION):
            result = WorkflowService.evaluate_property(Task.FIELD_PROP_VALUE_EXPRESSION, field, task)
            default = result

        # If no default exists, return None
        # Note: if default is False, we don't want to execute this code
        if default is None or (isinstance(default, str) and default.strip() == ''):
            if field.type == "enum" or field.type == "autocomplete":
                # Return empty arrays for multi-select
                if field.has_property(Task.FIELD_PROP_ENUM_TYPE) and \
                        field.get_property(Task.FIELD_PROP_ENUM_TYPE) == "checkbox":
                    return []
                else:
                    return None
            else:
                return None

        if field.type == "enum" and not has_lookup:
            default_option = next((obj for obj in field.options if obj.id == default), None)
            if not default_option:
                raise ApiError.from_task("invalid_default", "You specified a default value that does not exist in "
                                                            "the enum options ", task)
            return default
        elif field.type == "autocomplete" or field.type == "enum":
            lookup_model = LookupService.get_lookup_model(task, field)
            if field.has_property(Task.FIELD_PROP_LDAP_LOOKUP):  # All ldap records get the same person.
                return None # There is no default value for ldap.
            elif lookup_model:
                data = db.session.query(LookupDataModel).\
                    filter(LookupDataModel.lookup_file_model == lookup_model). \
                    filter(LookupDataModel.value == str(default)).\
                    first()
                if not data:
                    raise ApiError.from_task("invalid_default", "You specified a default value that does not exist in "
                                                                "the enum options ", task)
                return default
            else:
                raise ApiError.from_task("unknown_lookup_option", "The settings for this auto complete field "
                                                                 "are incorrect: %s " % field.id, task)
        elif field.type == "long":
            return int(default)
        elif field.type == 'boolean':
            default = str(default).lower()
            if default == 'true' or default == 't':
                return True
            return False
        elif field.type == 'date' and isinstance(default, datetime):
            return default.isoformat()
        else:
            return default

    @staticmethod
    def get_random_data_for_field(field, task):
        """Randomly populates the field,  mainly concerned with getting enums correct, as
        the rest are pretty easy."""
        has_lookup = WorkflowService.has_lookup(field)

        if field.type == "enum" and not has_lookup:
            # If it's a normal enum field with no lookup,
            # return a random option.
            if len(field.options) > 0:
                random_choice = random.choice(field.options)
                if isinstance(random_choice, dict):
                    random_value = random_choice['id']
                else:
                    # fixme: why it is sometimes an EnumFormFieldOption, and other times not?
                    random_value = random_choice.id
                if field.has_property(Task.FIELD_PROP_ENUM_TYPE) and field.get_property(Task.FIELD_PROP_ENUM_TYPE) == 'checkbox':
                    return [random_value]
                else:
                    return random_value

            else:
                raise ApiError.from_task("invalid_enum", "You specified an enumeration field (%s),"
                                                         " with no options" % field.id, task)
        elif field.type == "autocomplete" or field.type == "enum":
            # If it has a lookup, get the lookup model from the spreadsheet or task data, then return a random option
            # from the lookup model
            lookup_model = LookupService.get_lookup_model(task, field)
            if field.has_property(Task.FIELD_PROP_LDAP_LOOKUP):  # All ldap records get the same person.
                random_value = WorkflowService._random_ldap_record()
            elif lookup_model:
                data = db.session.query(LookupDataModel).filter(
                    LookupDataModel.lookup_file_model == lookup_model).limit(10).all()
                options = [{"value": d.value, "label": d.label, "data": d.data} for d in data]
                if len(options) > 0:
                    option = random.choice(options)
                    random_value = option['value']
                else:
                    raise ApiError.from_task("invalid enum", "You specified an enumeration field (%s),"
                                                             " with no options" % field.id, task)
            else:
                raise ApiError.from_task("unknown_lookup_option", "The settings for this auto complete field "
                                                                 "are incorrect: %s " % field.id, task)
            if field.has_property(Task.FIELD_PROP_ENUM_TYPE) and field.get_property(Task.FIELD_PROP_ENUM_TYPE) == 'checkbox':
                return [random_value]
            else:
                return random_value
        elif field.type == "long":
            return random.randint(1, 1000)
        elif field.type == 'boolean':
            return random.choice([True, False])
        elif field.type == 'file':
            doc_code = field.id
            if field.has_property('doc_code'):
                doc_code = WorkflowService.evaluate_property('doc_code', field, task)
            file_model = FileModel(name="test.png",
                                   irb_doc_code = field.id)
            doc_dict = DocumentService.get_dictionary()
            file = File.from_models(file_model, None, doc_dict)
            return FileSchema().dump(file)
        elif field.type == 'files':
            return random.randrange(1, 100)
        else:
            return WorkflowService._random_string()

    @staticmethod
    def _random_ldap_record():
        return {
            "label": "dhf8r",
            "value": "Dan Funk",
            "data": {
                "uid": "dhf8r",
                "display_name": "Dan Funk",
                "given_name": "Dan",
                "email_address": "dhf8r@virginia.edu",
                "department": "Department of Psychocosmographictology",
                "affiliation": "Roustabout",
                "sponsor_type": "Staff"}
        }


    @staticmethod
    def _random_string(string_length=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(string_length))

    @staticmethod
    def processor_to_workflow_api(processor: WorkflowProcessor, next_task=None):
        """Returns an API model representing the state of the current workflow, if requested, and
        possible, next_task is set to the current_task."""

        navigation = processor.bpmn_workflow.get_deep_nav_list()
        WorkflowService.update_navigation(navigation, processor)


        spec = db.session.query(WorkflowSpecModel).filter_by(id=processor.workflow_spec_id).first()
        is_review = FileService.is_workflow_review(processor.workflow_spec_id)
        workflow_api = WorkflowApi(
            id=processor.get_workflow_id(),
            status=processor.get_status(),
            next_task=None,
            navigation=navigation,
            workflow_spec_id=processor.workflow_spec_id,
            spec_version=processor.get_version_string(),
            is_latest_spec=processor.is_latest_spec,
            total_tasks=len(navigation),
            completed_tasks=processor.workflow_model.completed_tasks,
            last_updated=processor.workflow_model.last_updated,
            is_review=is_review,
            title=spec.display_name,
            study_id=processor.workflow_model.study_id or None
        )
        if not next_task:  # The Next Task can be requested to be a certain task, useful for parallel tasks.
            # This may or may not work, sometimes there is no next task to complete.
            next_task = processor.next_task()
        if next_task:
            previous_form_data = WorkflowService.get_previously_submitted_data(processor.workflow_model.id, next_task)
#            DeepMerge.merge(next_task.data, previous_form_data)
            next_task.data = DeepMerge.merge(previous_form_data, next_task.data)

            workflow_api.next_task = WorkflowService.spiff_task_to_api_task(next_task, add_docs_and_forms=True)
            # Update the state of the task to locked if the current user does not own the task.
            user_uids = WorkflowService.get_users_assigned_to_task(processor, next_task)
            if not UserService.in_list(user_uids, allow_admin_impersonate=True):
                workflow_api.next_task.state = WorkflowService.TASK_STATE_LOCKED
        return workflow_api

    @staticmethod
    def update_navigation(navigation: List[NavItem], processor: WorkflowProcessor):
        # Recursive function to walk down through children, and clean up descriptions, and statuses
        for nav_item in navigation:
            spiff_task = processor.bpmn_workflow.get_task(nav_item.task_id)
            if spiff_task:
                # Use existing logic to set the description, and alter the state based on permissions.
                api_task = WorkflowService.spiff_task_to_api_task(spiff_task, add_docs_and_forms=False)
                nav_item.description = api_task.title
                user_uids = WorkflowService.get_users_assigned_to_task(processor, spiff_task)
                if (isinstance(spiff_task.task_spec, UserTask) or isinstance(spiff_task.task_spec, ManualTask)) \
                        and not UserService.in_list(user_uids, allow_admin_impersonate=True):
                    nav_item.state = WorkflowService.TASK_STATE_LOCKED
            else:
                # Strip off the first word in the description, to meet guidlines for BPMN.
                if nav_item.description:
                    if nav_item.description is not None and ' ' in nav_item.description:
                        nav_item.description = nav_item.description.partition(' ')[2]

            # Recurse here
            WorkflowService.update_navigation(nav_item.children, processor)


    @staticmethod
    def get_previously_submitted_data(workflow_id, spiff_task):
        """ If the user has completed this task previously, find the form data for the last submission."""
        query = db.session.query(TaskEventModel) \
            .filter_by(workflow_id=workflow_id) \
            .filter_by(task_name=spiff_task.task_spec.name) \
            .filter_by(action=WorkflowService.TASK_ACTION_COMPLETE)

        if hasattr(spiff_task, 'internal_data') and 'runtimes' in spiff_task.internal_data:
            query = query.filter_by(mi_index=spiff_task.internal_data['runtimes'])

        latest_event = query.order_by(TaskEventModel.date.desc()).first()
        if latest_event:
            if latest_event.form_data is not None:
                return latest_event.form_data
            else:
                missing_form_error = (
                    f'We have lost data for workflow {workflow_id}, '
                    f'task {spiff_task.task_spec.name}, it is not in the task event model, '
                    f'and it should be.'
                )
                app.logger.error("missing_form_data", missing_form_error, exc_info=True)
                return {}
        else:
            return {}



    @staticmethod
    def spiff_task_to_api_task(spiff_task, add_docs_and_forms=False):
        task_type = spiff_task.task_spec.__class__.__name__

        task_types = [UserTask, ManualTask, BusinessRuleTask, CancelTask, ScriptTask, StartTask, EndEvent, StartEvent]

        for t in task_types:
            if isinstance(spiff_task.task_spec, t):
                task_type = t.__name__
                break
            else:
                task_type = "NoneTask"

        info = spiff_task.task_info()
        if info["is_looping"]:
            mi_type = MultiInstanceType.looping
        elif info["is_sequential_mi"]:
            mi_type = MultiInstanceType.sequential
        elif info["is_parallel_mi"]:
            mi_type = MultiInstanceType.parallel
        else:
            mi_type = MultiInstanceType.none

        props = {}
        if hasattr(spiff_task.task_spec, 'extensions'):
            for key, val in spiff_task.task_spec.extensions.items():
                props[key] = val

        if hasattr(spiff_task.task_spec, 'lane'):
            lane = spiff_task.task_spec.lane
        else:
            lane = None

        task = Task(spiff_task.id,
                    spiff_task.task_spec.name,
                    spiff_task.task_spec.description,
                    task_type,
                    spiff_task.get_state_name(),
                    lane,
                    None,
                    "",
                    {},
                    mi_type,
                    info["mi_count"],
                    info["mi_index"],
                    process_name=spiff_task.task_spec._wf_spec.description,
                    properties=props
                    )

        # Only process the form and documentation if requested.
        # The task should be in a completed or a ready state, and should
        # not be a previously completed MI Task.
        if add_docs_and_forms:
            task.data = spiff_task.data
            if hasattr(spiff_task.task_spec, "form"):
                task.form = spiff_task.task_spec.form
                for i, field in enumerate(task.form.fields):
                    task.form.fields[i] = WorkflowService.process_options(spiff_task, field)
                    # If there is a default value, set it.
                    if field.id not in task.data and WorkflowService.get_default_value(field, spiff_task) is not None:
                        task.data[field.id] = WorkflowService.get_default_value(field, spiff_task)
            task.documentation = WorkflowService._process_documentation(spiff_task)

        # All ready tasks should have a valid name, and this can be computed for
        # some tasks, particularly multi-instance tasks that all have the same spec
        # but need different labels.
        if spiff_task.state == SpiffTask.READY:
            task.properties = WorkflowService._process_properties(spiff_task, props)

        # Replace the title with the display name if it is set in the task properties,
        # otherwise strip off the first word of the task, as that should be following
        # a BPMN standard, and should not be included in the display.
        if task.properties and "display_name" in task.properties:
            try:
                task.title = spiff_task.workflow.script_engine.evaluate(spiff_task, task.properties[Task.PROP_EXTENSIONS_TITLE])
            except Exception as e:
                # if the task is ready, we should raise an error, but if it is in the future or the past, we may not
                # have the information we need to properly set the title, so don't error out, and just use what is
                # provided.
                if spiff_task.state == spiff_task.READY:
                    raise ApiError.from_task(code="task_title_error", message="Could not set task title on task %s with '%s' property because %s" %
                                                                  (spiff_task.task_spec.name, Task.PROP_EXTENSIONS_TITLE, str(e)), task=spiff_task)
                # Otherwise, just use the curreent title.
        elif task.title and ' ' in task.title:
            task.title = task.title.partition(' ')[2]

        if task.properties and "clear_data" in task.properties:
            if task.form and task.properties['clear_data'] == 'True':
                for i in range(len(task.form.fields)):
                    task.data.pop(task.form.fields[i].id, None)

        return task

    @staticmethod
    def _process_properties(spiff_task, props):
        """Runs all the property values through the Jinja2 processor to inject data."""
        for k, v in props.items():
            try:
                props[k] = JinjaService.get_content(v, spiff_task.data)
            except jinja2.exceptions.TemplateError as ue:
                app.logger.error(f'Failed to process task property {str(ue)}', exc_info=True)
        return props

    @staticmethod
    def _process_documentation(spiff_task):
        """Runs the given documentation string through the Jinja2 processor to inject data
        create loops, etc...  - If a markdown file exists with the same name as the task id,
        it will use that file instead of the documentation. """

        documentation = spiff_task.task_spec.documentation if hasattr(spiff_task.task_spec, "documentation") else ""

        try:
            doc_file_name = spiff_task.task_spec.name + ".md"
            data_model = FileService.get_workflow_file_data(spiff_task.workflow, doc_file_name)
            raw_doc = data_model.data.decode("utf-8")
        except ApiError:
            raw_doc = documentation

        if not raw_doc:
            return ""

        try:
            return JinjaService.get_content(raw_doc, spiff_task.data)
        except jinja2.exceptions.TemplateSyntaxError as tse:
            error_line = documentation.splitlines()[tse.lineno - 1]
            raise ApiError.from_task(code="template_error", message="Jinja Template Error:  %s" % str(tse),
                                     task=spiff_task, line_number=tse.lineno, error_line=error_line)
        except jinja2.exceptions.TemplateError as te:
            # Figure out the line number in the template that caused the error.
            cl, exc, tb = sys.exc_info()
            line_number = None
            error_line = None
            for frameSummary in traceback.extract_tb(tb):
                if frameSummary.filename == '<template>':
                    line_number = frameSummary.lineno
                    error_line = documentation.splitlines()[line_number - 1]
            raise ApiError.from_task(code="template_error", message="Jinja Template Error: %s" % str(te),
                                     task=spiff_task, line_number=line_number, error_line=error_line)
        except TypeError as te:
            raise ApiError.from_task(code="template_error", message="Jinja Template Error: %s" % str(te),
                                     task=spiff_task)
        except Exception as e:
            app.logger.error(str(e), exc_info=True)

    @staticmethod
    def process_options(spiff_task, field):
        if field.type != Task.FIELD_TYPE_ENUM:
            return field

        if hasattr(field, 'options') and len(field.options) > 1:
            return field
        elif not (field.has_property(Task.FIELD_PROP_VALUE_COLUMN) or
                field.has_property(Task.FIELD_PROP_LABEL_COLUMN)):
            raise ApiError.from_task("invalid_enum",
                                     f"For enumerations, you must include options, or a way to generate options from"
                                     f" a spreadsheet or data set. Please set either a spreadsheet name or data name,"
                                     f" along with the value and label columns to use from these sources.  Valid params"
                                     f" include: "
                                     f"{Task.FIELD_PROP_SPREADSHEET_NAME}, "
                                     f"{Task.FIELD_PROP_DATA_NAME}, "
                                     f"{Task.FIELD_PROP_VALUE_COLUMN}, "
                                     f"{Task.FIELD_PROP_LABEL_COLUMN}", task=spiff_task)

        if field.has_property(Task.FIELD_PROP_SPREADSHEET_NAME):
            lookup_model = LookupService.get_lookup_model(spiff_task, field)
            data = db.session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_model).all()
            for d in data:
                field.add_option(d.value, d.label)
        elif field.has_property(Task.FIELD_PROP_DATA_NAME):
            field.options = WorkflowService.get_options_from_task_data(spiff_task, field)


        return field

    @staticmethod
    def get_options_from_task_data(spiff_task, field):
        prop = field.get_property(Task.FIELD_PROP_DATA_NAME)
        if prop not in spiff_task.data:
            raise ApiError.from_task("invalid_enum", f"For enumerations based on task data, task data must have "
                                                     f"a property called {prop}", task=spiff_task)
        # Get the enum options from the task data
        data_model = spiff_task.data[prop]
        value_column = field.get_property(Task.FIELD_PROP_VALUE_COLUMN)
        label_column = field.get_property(Task.FIELD_PROP_LABEL_COLUMN)
        items = data_model.items() if isinstance(data_model, dict) else data_model
        options = []
        for item in items:
            if value_column not in item:
                raise ApiError.from_task("invalid_enum", f"The value column '{value_column}' does not exist for item {item}",
                                         task=spiff_task)
            if label_column not in item:
                raise ApiError.from_task("invalid_enum", f"The label column '{label_column}' does not exist for item {item}",
                                         task=spiff_task)

            options.append(Box({"id": item[value_column], "name": item[label_column], "data": item}))
        return options

    @staticmethod
    def update_task_assignments(processor):
        """For every upcoming user task, log a task action
        that connects the assigned user(s) to that task.  All
        existing assignment actions for this workflow are removed from the database,
        so that only the current valid actions are available. update_task_assignments
        should be called whenever progress is made on a workflow."""
        db.session.query(TaskEventModel). \
            filter(TaskEventModel.workflow_id == processor.workflow_model.id). \
            filter(TaskEventModel.action == WorkflowService.TASK_ACTION_ASSIGNMENT).delete()
        db.session.commit()

        for task in processor.get_current_user_tasks():
            user_ids = WorkflowService.get_users_assigned_to_task(processor, task)
            for user_id in user_ids:
                WorkflowService.log_task_action(user_id, processor, task, WorkflowService.TASK_ACTION_ASSIGNMENT)

    @staticmethod
    def get_users_assigned_to_task(processor, spiff_task) -> List[str]:
        if processor.workflow_model.study_id is None and processor.workflow_model.user_id is None:
            raise ApiError.from_task(code='invalid_workflow',
                                     message='A workflow must have either a study_id or a user_id.',
                                     task=spiff_task)
        # Standalone workflow - we only care about the current user
        elif processor.workflow_model.study_id is None and processor.workflow_model.user_id is not None:
            return [processor.workflow_model.user_id]
        # Workflow associated with a study - get all the users
        else:
            if not hasattr(spiff_task.task_spec, 'lane') or spiff_task.task_spec.lane is None:
                associated = StudyService.get_study_associates(processor.workflow_model.study.id)
                return [user.uid for user in associated if user.access]

            if spiff_task.task_spec.lane not in spiff_task.data:
                return []  # No users are assignable to the task at this moment
            lane_users = spiff_task.data[spiff_task.task_spec.lane]
            if not isinstance(lane_users, list):
                lane_users = [lane_users]

            lane_uids = []
            for user in lane_users:
                if isinstance(user, dict):
                    if user.get("value"):
                        lane_uids.append(user['value'])
                    else:
                        raise ApiError.from_task(code="task_lane_user_error", message="Spiff Task %s lane user dict must have a key called 'value' with the user's uid in it." %
                                                                  spiff_task.task_spec.name, task=spiff_task)
                elif isinstance(user, str):
                    lane_uids.append(user)
                else:
                    raise ApiError.from_task(code="task_lane_user_error", message="Spiff Task %s lane user is not a string or dict" %
                                                                  spiff_task.task_spec.name, task=spiff_task)

            return lane_uids

    @staticmethod
    def log_task_action(user_uid, processor, spiff_task, action):
        task = WorkflowService.spiff_task_to_api_task(spiff_task)
        form_data = WorkflowService.extract_form_data(spiff_task.data, spiff_task)
        task_event = TaskEventModel(
            study_id=processor.workflow_model.study_id,
            user_uid=user_uid,
            workflow_id=processor.workflow_model.id,
            workflow_spec_id=processor.workflow_model.workflow_spec_id,
            spec_version=processor.get_version_string(),
            action=action,
            task_id=task.id,
            task_name=task.name,
            task_title=task.title,
            task_type=str(task.type),
            task_state=task.state,
            task_lane=task.lane,
            form_data=form_data,
            mi_type=task.multi_instance_type.value,  # Some tasks have a repeat behavior.
            mi_count=task.multi_instance_count,  # This is the number of times the task could repeat.
            mi_index=task.multi_instance_index,  # And the index of the currently repeating task.
            process_name=task.process_name,
            # date=datetime.utcnow(), <=== For future reference, NEVER do this. Let the database set the time.
        )
        db.session.add(task_event)
        db.session.commit()

    @staticmethod
    def extract_form_data(latest_data, task):
        """Extracts data from the latest_data that is directly related to the form that is being
        submitted."""
        data = {}

        if hasattr(task.task_spec, 'form'):
            for field in task.task_spec.form.fields:
                if field.has_property(Task.FIELD_PROP_REPEAT):
                    group = field.get_property(Task.FIELD_PROP_REPEAT)
                    if group in latest_data:
                        data[group] = latest_data[group]
                else:
                    value = WorkflowService.get_dot_value(field.id, latest_data)
                    if value is not None:
                        WorkflowService.set_dot_value(field.id, value, data)
        return data

    @staticmethod
    def get_dot_value(path, source):
        ### Given a path in dot notation, uas as 'fruit.type' tries to find that value in
        ### the source, but looking deep in the dictionary.
        paths = path.split(".")  # [a,b,c]
        s = source
        index = 0
        for p in paths:
            index += 1
            if isinstance(s, dict) and p in s:
                if index == len(paths):
                    return s[p]
                else:
                    s = s[p]
        if path in source:
            return source[path]
        return None


    @staticmethod
    def set_dot_value(path, value, target):
        ### Given a path in dot notation, such as "fruit.type", and a value "apple", will
        ### set the value in the target dictionary, as target["fruit"]["type"]="apple"
        destination = target
        paths = path.split(".")  # [a,b,c]
        index = 0
        for p in paths:
            index += 1
            if p not in destination:
                if index == len(paths):
                    destination[p] = value
                else:
                    destination[p] = {}
            destination = destination[p]
        return target


    @staticmethod
    def process_workflows_for_cancels(study_id):
        workflows = db.session.query(WorkflowModel).filter_by(study_id=study_id).all()
        for workflow in workflows:
            if workflow.status == WorkflowStatus.user_input_required or workflow.status == WorkflowStatus.waiting:
                WorkflowProcessor.reset(workflow, clear_data=False)

    @staticmethod
    def get_workflow_from_spec(workflow_spec_id, user):
        workflow_model = WorkflowModel(status=WorkflowStatus.not_started,
                                       study=None,
                                       user_id=user.uid,
                                       workflow_spec_id=workflow_spec_id,
                                       last_updated=datetime.now())
        db.session.add(workflow_model)
        db.session.commit()
        return workflow_model

    @staticmethod
    def get_standalone_workflow_specs():
        specs = db.session.query(WorkflowSpecModel).filter_by(standalone=True).all()
        return specs

    @staticmethod
    def get_library_workflow_specs():
        specs = db.session.query(WorkflowSpecModel).filter_by(library=True).all()
        return specs

    @staticmethod
    def get_primary_workflow(workflow_spec_id):
        # Returns the FileModel of the primary workflow for a workflow_spec
        primary = None
        file = db.session.query(FileModel).filter(FileModel.workflow_spec_id==workflow_spec_id, FileModel.primary==True).first()
        if file:
            primary = file
        return primary

    @staticmethod
    def reorder_workflow_spec(spec, direction):
        category_id = spec.category_id
        # Direction is either `up` or `down`
        # This is checked in api.workflow.reorder_workflow_spec
        if direction == 'up':
            neighbor = session.query(WorkflowSpecModel). \
                filter(WorkflowSpecModel.category_id == category_id). \
                filter(WorkflowSpecModel.display_order == spec.display_order - 1). \
                first()
            if neighbor:
                neighbor.display_order += 1
                spec.display_order -= 1
        if direction == 'down':
            neighbor = session.query(WorkflowSpecModel). \
                filter(WorkflowSpecModel.category_id == category_id). \
                filter(WorkflowSpecModel.display_order == spec.display_order + 1). \
                first()
            if neighbor:
                neighbor.display_order -= 1
                spec.display_order += 1
        if neighbor:
            session.add(spec)
            session.add(neighbor)
            session.commit()
        ordered_specs = session.query(WorkflowSpecModel). \
            filter(WorkflowSpecModel.category_id == category_id). \
            order_by(WorkflowSpecModel.display_order).all()
        return ordered_specs

    @staticmethod
    def reorder_workflow_spec_category(category, direction):
        # Direction is either `up` or `down`
        # This is checked in api.workflow.reorder_workflow_spec_category
        if direction == 'up':
            neighbor = session.query(WorkflowSpecCategoryModel).\
                filter(WorkflowSpecCategoryModel.display_order == category.display_order - 1).\
                first()
            if neighbor:
                neighbor.display_order += 1
                category.display_order -= 1
        if direction == 'down':
            neighbor = session.query(WorkflowSpecCategoryModel).\
                filter(WorkflowSpecCategoryModel.display_order == category.display_order + 1).\
                first()
            if neighbor:
                neighbor.display_order -= 1
                category.display_order += 1
        if neighbor:
            session.add(neighbor)
            session.add(category)
            session.commit()
        ordered_categories = session.query(WorkflowSpecCategoryModel).\
            order_by(WorkflowSpecCategoryModel.display_order).all()
        return ordered_categories

    @staticmethod
    def cleanup_workflow_spec_display_order(category_id):
        # make sure we don't have gaps in display_order
        new_order = 0
        specs = session.query(WorkflowSpecModel).\
            filter(WorkflowSpecModel.category_id == category_id).\
            order_by(WorkflowSpecModel.display_order).all()
        for spec in specs:
            spec.display_order = new_order
            session.add(spec)
            new_order += 1
        session.commit()

    @staticmethod
    def cleanup_workflow_spec_category_display_order():
        # make sure we don't have gaps in display_order
        new_order = 0
        categories = session.query(WorkflowSpecCategoryModel).\
            order_by(WorkflowSpecCategoryModel.display_order).all()
        for category in categories:
            category.display_order = new_order
            session.add(category)
            new_order += 1
        session.commit()

    @staticmethod
    def delete_workflow_spec_files(spec_id):
        files = session.query(FileModel).filter_by(workflow_spec_id=spec_id).all()
        for file in files:
            FileService.delete_file(file.id)

    @staticmethod
    def delete_workflow_spec_task_events(spec_id):
        session.query(TaskEventModel).filter(TaskEventModel.workflow_spec_id == spec_id).delete()
        session.commit()

    @staticmethod
    def delete_workflow_spec_workflow_models(spec_id):
        for workflow in session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id):
            StudyService.delete_workflow(workflow.id)
