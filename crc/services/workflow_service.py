import copy
import json
import random
import string
import sys
import traceback
from datetime import datetime
from typing import List

import jinja2
from SpiffWorkflow.task import Task as SpiffTask,  TaskState, TaskStateNames
from SpiffWorkflow.exceptions import WorkflowException
from SpiffWorkflow.bpmn.PythonScriptEngine import Box
from SpiffWorkflow.bpmn.specs.ManualTask import ManualTask
from SpiffWorkflow.bpmn.specs.ScriptTask import ScriptTask
from SpiffWorkflow.bpmn.specs.UserTask import UserTask
from SpiffWorkflow.bpmn.specs.events.EndEvent import EndEvent
from SpiffWorkflow.bpmn.specs.events.StartEvent import StartEvent
from SpiffWorkflow.dmn.specs.BusinessRuleTask import BusinessRuleTask
from SpiffWorkflow.bpmn.exceptions import WorkflowTaskExecException
from SpiffWorkflow.specs import CancelTask, StartTask
from SpiffWorkflow.util.deep_merge import DeepMerge
from sentry_sdk import capture_message, push_scope
from sqlalchemy.exc import InvalidRequestError

from crc import db, app, session
from crc.api.common import ApiError
from crc.models.api_models import Task, MultiInstanceType, WorkflowApi
from crc.models.file import LookupDataModel, FileModel, File, FileSchema
from crc.models.ldap import LdapModel
from crc.models.nav_item import NavItem
from crc.models.study import StudyModel
from crc.models.task_event import TaskEventModel, TaskAction
from crc.models.user import UserModel
from crc.models.workflow import WorkflowModel, WorkflowStatus, WorkflowState
from crc.services.data_store_service import DataStoreBase
from crc.services.document_service import DocumentService
from crc.services.jinja_service import JinjaService
from crc.services.ldap_service import LdapService
from crc.services.lookup_service import LookupService
from crc.services.spec_file_service import SpecFileService
from crc.services.study_service import StudyService
from crc.services.user_service import UserService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_spec_service import WorkflowSpecService

from flask import g


class WorkflowService(object):

    TASK_STATE_LOCKED = "LOCKED"  # When the task belongs to a different user.

    """Provides tools for processing workflows and tasks.  This
     should at some point, be the only way to work with Workflows, and
     the workflow Processor should be hidden behind this service.
     This will help maintain a structure that avoids circular dependencies.
     But for now, this contains tools for converting spiff-workflow models into our
     own API models with additional information and capabilities and
     handles the testing of a workflow specification by completing it with
     random selections, attempting to mimic a front end as much as possible. """

    @staticmethod
    def make_test_workflow(spec_id, validate_study_id=None):
        try:
            user = UserService.current_user()
        except ApiError:
            user = None
        if not user:
            user = db.session.query(UserModel).filter_by(uid="test").first()
        if not user:
            db.session.add(LdapModel(uid="test"))
            db.session.add(UserModel(uid="test"))
            db.session.commit()
            user = db.session.query(UserModel).filter_by(uid="test").first()
        if validate_study_id is not None:
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
        db.session.add(workflow_model)
        db.session.commit()
        return workflow_model

    @staticmethod
    def delete_test_data(workflow: WorkflowModel):
        try:
            db.session.delete(workflow)
        except InvalidRequestError:
            pass
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
        records = db.session.query(WorkflowModel).filter(WorkflowModel.status == WorkflowStatus.waiting).all()
        for workflow_model in records:
            try:
                app.logger.info('Processing workflow %s' % workflow_model.id)
                processor = WorkflowProcessor(workflow_model)
                processor.bpmn_workflow.refresh_waiting_tasks()
                processor.bpmn_workflow.do_engine_steps()
                processor.save()
            except Exception as e:
                db.session.rollback()  # in case the above left the database with a bad transaction
                workflow_model.status = WorkflowStatus.erroring
                db.session.add(workflow_model)
                db.session.commit()
                app.logger.error(f"Error running waiting task for workflow #%i (%s) for study #%i.  %s" %
                                 (workflow_model.id,
                                  workflow_model.workflow_spec_id,
                                  workflow_model.study_id,
                                  str(e)))

    @staticmethod
    def get_erroring_workflows():
        workflows = session.query(WorkflowModel).filter(WorkflowModel.status == WorkflowStatus.erroring).all()
        return workflows

    @staticmethod
    def get_workflow_url(workflow):
        base_url = app.config['FRONTEND']
        workflow_url = f'https://{base_url}/workflow/{workflow.id}'
        return workflow_url

    def process_erroring_workflows(self):
        with app.app_context():    
            workflows = self.get_erroring_workflows()
            if len(workflows) > 0:
                workflow_urls = []
                if len(workflows) == 1:
                    workflow = workflows[0]
                    workflow_url_link = self.get_workflow_url(workflow)
                    workflow_urls.append(workflow_url_link)
                    message = 'There is one workflow in an error state.'
                    message += f'\n You can restart the workflow at {workflow_url_link}.'
                else:
                    message = f'There are {len(workflows)} workflows in an error state.'
                    message += '\nYou can restart the workflows at these URLs:'
                    for workflow in workflows:
                        workflow_url_link = self.get_workflow_url(workflow)
                        workflow_urls.append(workflow_url_link)
                        message += f'\n{workflow_url_link}'
    
                with push_scope() as scope:
                    scope.user = {"urls": workflow_urls}
                    scope.set_extra("workflow_urls", workflow_urls)
                    # this sends a message through sentry
                    capture_message(message)
                # We return message so we can use it in a test
                return message

    @staticmethod
    def test_spec(spec_id, validate_study_id=None, test_until=None, required_only=False):
        """Runs a spec through its paces to see if it results in any errors.
          Not fool-proof, but a good sanity check.  Returns the final data
          output form the last task if successful.

          test_until - stop running the validation when you reach this task spec.

          required_only can be set to true, in which case this will run the
          spec, only completing the required fields, rather than everything.
          """

        g.validation_data_store = []

        workflow_model = WorkflowService.make_test_workflow(spec_id, validate_study_id)
        try:
            processor = WorkflowProcessor(workflow_model, validate_only=True)
            count = 0

            while not processor.bpmn_workflow.is_completed():
                exit_task = processor.bpmn_workflow.do_engine_steps(exit_at=test_until)
                if (exit_task != None):
                    raise ApiError.from_task("validation_break",
                                             f"The validation has been exited early on task '{exit_task.task_spec.id}' "
                                             f"and was parented by ",
                                             exit_task.parent)
                tasks = processor.bpmn_workflow.get_tasks(TaskState.READY)
                for task in tasks:
                    if task.task_spec.lane is not None and task.task_spec.lane not in task.data:
                        raise ApiError.from_task("invalid_role",
                                                 f"This task is in a lane called '{task.task_spec.lane}', The "
                                                 f" current task data must have information mapping this role to "
                                                 f" a unique user id.", task)
                    if task.task_spec.lane is not None:
                        if isinstance(task.data[task.task_spec.lane], str) and not LdapService().user_exists(
                                task.data[task.task_spec.lane]):
                            raise ApiError.from_task("missing_user",
                                                     f"The user '{task.data[task.task_spec.lane]}' "
                                                     f"could not be found in LDAP. ", task)
                        elif isinstance(task.data[task.task_spec.lane], list):
                            for uid in task.data[task.task_spec.lane]:
                                if not LdapService().user_exists(uid):
                                    raise ApiError.from_task("missing_user",
                                                             f"The user '{uid}' "
                                                             f"could not be found in LDAP. ", task)

                    task_api = WorkflowService.spiff_task_to_api_task(
                        task,
                        add_docs_and_forms=True)  # Assure we try to process the documentation, and raise those errors.
                    # make sure forms have a form key
                    if hasattr(task_api, 'form') and task_api.form is not None:
                        if task_api.form.key == '':
                            raise ApiError(code='missing_form_key',
                                           message='Forms must include a Form Key.',
                                           task_id=task.id,
                                           task_name=task.get_name())
                        WorkflowService.populate_form_with_random_data(task, task_api, required_only)
                        if not WorkflowService.validate_form(task, task_api):
                            # In the process of completing the form, it is possible for fields to become required
                            # based on later fields.  If the form has incomplete, but required fields (validate_form)
                            # then try to populate the form again, with this new information.
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
        except ApiError:
            # Raising because we have some tests that depend on it
            raise
        except Exception as e:
            # Catch generic exceptions so that the finally clause always executes
            app.logger.error(f'Unexpected exception caught during validation. Original exception: {str(e)}',
                             exc_info=True)
            raise ApiError(code='unknown_exception',
                           message=f'We caught an unexpected exception during validation. Original exception is: {str(e)}')
        finally:
            WorkflowService.delete_test_data(workflow_model)
        return processor.bpmn_workflow.last_task.data

    @staticmethod
    def validate_form(task, task_api):
        for field in task_api.form.fields:
            if WorkflowService.is_required_field(field, task):
                if not field.id in task.data or task.data[field.id] is None:
                    return False
        return True

    @staticmethod
    def is_required_field(field, task):
        # Get Required State
        is_required = False
        if (field.has_validation(Task.FIELD_CONSTRAINT_REQUIRED) and
                field.get_validation(Task.FIELD_CONSTRAINT_REQUIRED)):
            is_required = True
        if (field.has_property(Task.FIELD_PROP_REQUIRED_EXPRESSION) and
                WorkflowService.evaluate_property(Task.FIELD_PROP_REQUIRED_EXPRESSION, field, task)):
            is_required = True
        return is_required

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
            form_data[field.id] = None

        for field in task_api.form.fields:
            is_required = WorkflowService.is_required_field(field, task)

            # Assure we have a field type
            if field.type is None:
                raise ApiError(code='invalid_form_data',
                               message=f'Type is missing for field "{field.id}". A field type must be provided.',
                               task_id=task.id,
                               task_name=task.get_name())
                # Assure we have valid ids
            if not WorkflowService.check_field_id(field.id):
                raise ApiError(code='invalid_form_id',
                               message=f'Invalid Field name: "{field.id}".  A field ID must begin with a letter, '
                                       f'and can only contain letters, numbers, and "_"',
                               task_id=task.id,
                               task_name=task.get_name())
            # Assure field has valid properties
            WorkflowService.check_field_properties(field, task)
            WorkflowService.check_field_type(field, task)

            # If we have a label, try to set the label
            if field.label:
                try:
                    # Assure that we can evaluate the field.label, but no need to save the resulting value.
                    task.workflow.script_engine._evaluate(field.label, form_data, task)
                except Exception as e:
                    raise ApiError.from_task("bad label", f'The label "{field.label}" in field {field.id} '
                                                          f'could not be understood or evaluated. ',
                                             task=task)

            # If a field is hidden and required, it must have a default value
            # if field.has_property(Task.FIELD_PROP_HIDE_EXPRESSION) and field.has_validation(
            #         Task.FIELD_CONSTRAINT_REQUIRED):
            #     if field.default_value is None:
            #         raise ApiError(code='hidden and required field missing default',
            #                        message=f'Field "{field.id}" is required but can be hidden. It must have a def1ault value.',
            #                        task_id='task.id',
            #                        task_name=task.get_name())

            # If we have a default_value, try to set the default
            if field.default_value:
                try:
                    form_data[field.id] = WorkflowService.get_default_value(field, task, data)
                except Exception as e:
                    raise ApiError.from_task("bad default value",
                                             f'The default value "{field.default_value}" in field {field.id} '
                                             f'could not be understood or evaluated. ',
                                             task=task)
                # If we have a good default value, and we aren't dealing with a repeat, we can stop here.
                if form_data[field.id] is not None and not field.has_property(Task.FIELD_PROP_REPEAT):
                    continue
            else:
                form_data[field.id] = None

            # If the field is hidden we can leave it as none.
            if field.has_property(Task.FIELD_PROP_HIDE_EXPRESSION):

                if WorkflowService.evaluate_property(Task.FIELD_PROP_HIDE_EXPRESSION, field, task, form_data):
                    continue

            # If we are only populating required fields, and this isn't required. stop here.
            if required_only:
                if not is_required:
                    continue  # Don't include any fields that aren't specifically marked as required.

            # If it is read only, stop here.
            if field.has_property("read_only") and field.get_property(
                    Task.FIELD_PROP_READ_ONLY).lower().strip() == "true":
                continue  # Don't mess about with read only fields.

            if field.has_property(Task.FIELD_PROP_REPEAT) and field.has_property(Task.FIELD_PROP_GROUP):
                raise ApiError.from_task("group_repeat", f'Fields cannot have both group and repeat properties. '
                                                         f' Please remove one of these properties. ',
                                         task=task)

            if field.has_property(Task.FIELD_PROP_REPEAT):
                group = field.get_property(Task.FIELD_PROP_REPEAT)
                if group in form_data and not (isinstance(form_data[group], list)):
                    raise ApiError.from_task("invalid_group",
                                             f'You are grouping form fields inside a variable that is defined '
                                             f'elsewhere: {group}.  Be sure that you use a unique name for the '
                                             f'for repeat and group expressions that is not also used for a field name.'
                                             , task=task)
                if field.has_property(Task.FIELD_PROP_REPEAT_HIDE_EXPRESSION):
                    result = WorkflowService.evaluate_property(Task.FIELD_PROP_REPEAT_HIDE_EXPRESSION, field, task,
                                                               form_data)
                    if not result:
                        hide_groups.append(group)
                if group not in form_data and group not in hide_groups:
                    form_data[group] = [{}, {}, {}]
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
            if field.has_property(Task.FIELD_PROP_REPEAT) and field.get_property(
                    Task.FIELD_PROP_REPEAT) in task.data.keys():
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
            doc_code = task.workflow.script_engine._evaluate(field.get_property(Task.FIELD_PROP_DOC_CODE), data, task)
            file = db.session.query(FileModel).filter(FileModel.id == file_id).first()
            if (file):
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
            DataStoreBase().set_data_common('file', field.id, data[field.id], task.id, None, None, None, file_id)

    @staticmethod
    def evaluate_property(property_name, field, task, task_data=None):
        expression = field.get_property(property_name)
        if not task_data:
            task_data = task.data
        data = copy.deepcopy(task_data)
        # If there's a field key with no initial value, give it one (None)
        for other_field in task.task_spec.form.fields:
            if other_field.id not in data:
                data[other_field.id] = None

        if field.has_property(Task.FIELD_PROP_REPEAT):
            # Then you must evaluate the expression based on the data within the group, if that data exists.
            # There may not be data available in the group, if no groups were added
            group = field.get_property(Task.FIELD_PROP_REPEAT)
            if group in task_data and len(task_data[group]) > 0:
                # Here we must make the current group data top level (as it would be in a repeat section) but
                # make all other top level task data available as well.
                new_data = copy.deepcopy(task_data)
                del (new_data[group])
                data = task_data[group][0]
                data.update(new_data)
            else:
                return None  # We may not have enough information to process this

        if not field.has_property(Task.FIELD_PROP_REPEAT):
            new_data = copy.deepcopy(task.data)

        try:
            return task.workflow.script_engine._evaluate(expression, data, task)
        except Exception as e:
            message = f"The field {field.id} contains an invalid expression: '{expression}'.  {e}"
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
    def get_default_value(field, task, data):
        has_lookup = WorkflowService.has_lookup(field)
        # default = WorkflowService.evaluate_property(Task.FIELD_PROP_VALUE_EXPRESSION, field, task)
        default = None
        if field.default_value is not None:
            try:
                default = task.workflow.script_engine._evaluate(field.default_value, data, task)
            except Exception as e:
                raise WorkflowTaskExecException(task, "invalid_default", e)
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
                return None  # There is no default value for ldap.
            elif lookup_model:
                data = db.session.query(LookupDataModel). \
                    filter(LookupDataModel.lookup_file_model == lookup_model). \
                    filter(LookupDataModel.value == str(default)). \
                    first()
                if not data:
                    raise ApiError.from_task("invalid_default", "You specified a default value that does not exist in "
                                                                "the enum options ", task)
                return default
            else:
                raise ApiError.from_task("unknown_lookup_option", "The settings for this auto complete field "
                                                                  "are incorrect: %s " % field.id, task)
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
                if field.has_property(Task.FIELD_PROP_ENUM_TYPE) and field.get_property(
                        Task.FIELD_PROP_ENUM_TYPE) == 'checkbox':
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
            if field.has_property(Task.FIELD_PROP_ENUM_TYPE) and field.get_property(
                    Task.FIELD_PROP_ENUM_TYPE) == 'checkbox':
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
                                   irb_doc_code=field.id)
            doc_dict = DocumentService.get_dictionary()
            file = File.from_file_model(file_model, doc_dict)
            return FileSchema().dump(file)
        elif field.type == 'files':
            return random.randrange(1, 100)
        elif field.type == 'date':
            return datetime.utcnow()
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
    def get_navigation(processor):
        """Finds all the ready, completed, and future tasks and created nav_item objects for them."""
        tasks = []
        navigation = []
        # Get ready, completed, and fuiture tasks
        tasks.extend(processor.bpmn_workflow.get_tasks(TaskState.READY | TaskState.COMPLETED | TaskState.FUTURE))

        # Filter this out to just the user tasks and the start task
        user_tasks = list(filter(lambda task: isinstance(task.task_spec, UserTask)
                                              or isinstance(task.task_spec, ManualTask)
                                              or isinstance(task.task_spec, StartEvent), tasks))

        for user_task in user_tasks:
            if any(nav.name == user_task.task_spec.name and user_task.state == TaskState.FUTURE for nav in navigation):
                continue  # Don't re-add the same spec for future items
            nav_item = NavItem.from_spec(spec=user_task.task_spec)
            nav_item.state = TaskStateNames[user_task.state]
            nav_item.task_id = user_task.id
            nav_item.indent = 0  # we should remove indent, this is not nested now.
            navigation.append(nav_item)
        WorkflowService.update_navigation(navigation, processor)
        return navigation

    @staticmethod
    def get_workflow_user_id(workflow_id):
        user_id = db.session.query(WorkflowModel.user_id).\
            filter(WorkflowModel.id == workflow_id).scalar()
        return user_id

    @staticmethod
    def processor_to_workflow_api(processor: WorkflowProcessor, next_task=None):
        """Returns an API model representing the state of the current workflow, if requested, and
        possible, next_task is set to the current_task."""
        # navigation = processor.bpmn_workflow.get_deep_nav_list()
        # WorkflowService.update_navigation(navigation, processor)
        spec_service = WorkflowSpecService()
        spec = spec_service.get_spec(processor.workflow_spec_id)
        is_admin_workflow = WorkflowService.is_admin_workflow(processor.workflow_spec_id)
        workflow_id = processor.get_workflow_id()
        user_id = WorkflowService.get_workflow_user_id(workflow_id)
        workflow_api = WorkflowApi(
            id=workflow_id,
            status=processor.get_status(),
            next_task=None,
            navigation=WorkflowService.get_navigation(processor),
            workflow_spec_id=processor.workflow_spec_id,
            last_updated=processor.workflow_model.last_updated,
            is_review=spec.is_review,
            title=spec.display_name,
            study_id=processor.workflow_model.study_id or None,
            state=processor.workflow_model.state,
            user_id=user_id,
            is_admin_workflow=is_admin_workflow
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
                nav_item.description = WorkflowService.__calculate_title(spiff_task)
                user_uids = WorkflowService.get_users_assigned_to_task(processor, spiff_task)
                if (isinstance(spiff_task.task_spec, UserTask) or isinstance(spiff_task.task_spec, ManualTask)) \
                        and not UserService.in_list(user_uids, allow_admin_impersonate=True):
                    nav_item.state = WorkflowService.TASK_STATE_LOCKED
                if isinstance(spiff_task.task_spec, StartEvent) and nav_item.lane:
                    in_list = UserService.in_list(user_uids, allow_admin_impersonate=True)
                    impersonator_is_admin = UserService.user_is_admin(allow_admin_impersonate=True)
                    if not in_list and not impersonator_is_admin:
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
            .filter_by(action=TaskAction.COMPLETE.value)

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
        task_type = spiff_task.task_spec.spec_type

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
                    # if field.id not in task.data and WorkflowService.get_default_value(field, spiff_task) is not None:
                    #    task.data[field.id] = WorkflowService.get_default_value(field, spiff_task)
            task.documentation = WorkflowService._process_documentation(spiff_task)

        # All ready tasks should have a valid name, and this can be computed for
        # some tasks, particularly multi-instance tasks that all have the same spec
        # but need different labels.
        if spiff_task.state == TaskState.READY:
            task.properties = WorkflowService._process_properties(spiff_task, props)

        task.title = WorkflowService.__calculate_title(spiff_task)

        if task.properties and "clear_data" in task.properties:
            if task.form and task.properties['clear_data'] == 'True':
                for i in range(len(task.form.fields)):
                    task.data.pop(task.form.fields[i].id, None)

        # Pass help text through the Jinja parser
        if task.form and task.form.fields:
            for field in task.form.fields:
                if field.properties:
                    for field_property in field.properties:
                        if field_property.id == 'help':
                            jinja_text = JinjaService().get_content(field_property.value, task.data)
                            field_property.value = jinja_text

        return task

    @staticmethod
    def __calculate_title(spiff_task):
        title = spiff_task.task_spec.description or None
        if hasattr(spiff_task.task_spec, 'extensions') and "display_name" in spiff_task.task_spec.extensions:
            title = spiff_task.task_spec.extensions["display_name"]
            try:
                title = JinjaService.get_content(title, spiff_task.data)
                title = spiff_task.workflow.script_engine.evaluate(spiff_task, title)
            except Exception as e:
                # if the task is ready, we should raise an error, but if it is in the future or the past, we may not
                # have the information we need to properly set the title, so don't error out, and just use the base
                # description for now.
                title = spiff_task.task_spec.description
                if spiff_task.state == TaskState.READY:
                    raise ApiError.from_task(code="task_title_error",
                                             message="Could not set task title on task %s with '%s' property because %s" %
                                                     (spiff_task.task_spec.name, Task.PROP_EXTENSIONS_TITLE, str(e)),
                                             task=spiff_task)
        elif title and ' ' in title:
            title = title.partition(' ')[2]
        return title

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
    def workflow_id_from_spiff_task(spiff_task):
        workflow = spiff_task.workflow
        # Find the top level workflow
        while WorkflowProcessor.WORKFLOW_ID_KEY not in workflow.data:
            if workflow.outer_workflow != workflow:
                workflow = workflow.outer_workflow
            else:
                break
        return workflow.data[WorkflowProcessor.WORKFLOW_ID_KEY]

    @staticmethod
    def _process_documentation(spiff_task):
        """Runs the given documentation string through the Jinja2 processor to inject data
        create loops, etc...  - If a markdown file exists with the same name as the task id,
        it will use that file instead of the documentation. """

        documentation = spiff_task.task_spec.documentation if hasattr(spiff_task.task_spec, "documentation") else ""

        try:
            doc_file_name = spiff_task.task_spec.name + ".md"

            workflow_id = WorkflowService.workflow_id_from_spiff_task(spiff_task)
            workflow = db.session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
            spec_service = WorkflowSpecService()
            data = SpecFileService.get_data(spec_service.get_spec(workflow.workflow_spec_id), doc_file_name)
            raw_doc = data.decode("utf-8")
        except ApiError:
            raw_doc = documentation

        if not raw_doc:
            return ""

        try:
            return JinjaService.get_content(raw_doc, spiff_task.data)
        except jinja2.exceptions.TemplateSyntaxError as tse:
            lines = tse.source.splitlines()
            error_line = ""
            if len(lines) >= tse.lineno - 1:
                error_line = tse.source.splitlines()[tse.lineno - 1]
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
                    lines = documentation.splitlines()
                    error_line = ""
                    if len(lines) > line_number:
                        error_line = lines[line_number - 1]
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
                raise ApiError.from_task("invalid_enum",
                                         f"The value column '{value_column}' does not exist for item {item}",
                                         task=spiff_task)
            if label_column not in item:
                raise ApiError.from_task("invalid_enum",
                                         f"The label column '{label_column}' does not exist for item {item}",
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
            filter(TaskEventModel.action == TaskAction.ASSIGNMENT.value).delete()
        db.session.commit()

        tasks = processor.get_current_user_tasks()
        for task in tasks:
            user_ids = WorkflowService.get_users_assigned_to_task(processor, task)
            for user_id in user_ids:
                WorkflowService.log_task_action(user_id, processor, task, TaskAction.ASSIGNMENT.value)

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
                        raise ApiError.from_task(code="task_lane_user_error",
                                                 message="Spiff Task %s lane user dict must have a key called 'value' with the user's uid in it." %
                                                         spiff_task.task_spec.name, task=spiff_task)
                elif isinstance(user, str):
                    lane_uids.append(user)
                else:
                    raise ApiError.from_task(code="task_lane_user_error",
                                             message="Spiff Task %s lane user is not a string or dict" %
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
    def update_workflow_state_from_master_workflow(study_id, master_workflow_results):
        # Create a dictionary of workflows for this study, keyed by workflow_spec_id
        wf_by_workflow_spec_id = {}
        workflows = session.query(WorkflowModel).filter(WorkflowModel.study_id == study_id).all()
        for workflow in workflows:
            wf_by_workflow_spec_id[workflow.workflow_spec_id] = workflow
        # Update the workflow states with results from master workflow
        for workflow_spec_id in master_workflow_results:
            # only process the workflows (there are other things in master_workflow_results)
            if workflow_spec_id in wf_by_workflow_spec_id:
                workflow_state = master_workflow_results[workflow_spec_id]['status']
                workflow_state_message = master_workflow_results[workflow_spec_id]['message']
                # Make sure we have a valid state
                if WorkflowState.has_value(workflow_state):
                    # Get the workflow from our dictionary and set the state
                    workflow = wf_by_workflow_spec_id[workflow_spec_id]
                    workflow.state = workflow_state
                    workflow.state_message = workflow_state_message
                    session.add(workflow)

        session.commit()

    @staticmethod
    def get_workflow_spec_category(workflow_spec_id):
        workflow_spec = WorkflowSpecService().get_spec(workflow_spec_id)
        category_id = workflow_spec.category_id
        category = WorkflowSpecService().get_category(category_id)
        return category

    @staticmethod
    def is_admin_workflow(workflow_spec_id):
        category = WorkflowService.get_workflow_spec_category(workflow_spec_id)
        return category.admin
