import copy
import json
import string
import uuid
from datetime import datetime
import random

import jinja2
from SpiffWorkflow import Task as SpiffTask, WorkflowException
from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent
from SpiffWorkflow.bpmn.specs.ManualTask import ManualTask
from SpiffWorkflow.bpmn.specs.MultiInstanceTask import MultiInstanceTask
from SpiffWorkflow.bpmn.specs.ScriptTask import ScriptTask
from SpiffWorkflow.bpmn.specs.StartEvent import StartEvent
from SpiffWorkflow.bpmn.specs.UserTask import UserTask
from SpiffWorkflow.dmn.specs.BusinessRuleTask import BusinessRuleTask
from SpiffWorkflow.specs import CancelTask, StartTask
from SpiffWorkflow.util.deep_merge import DeepMerge
from flask import g
from jinja2 import Template

from crc import db, app
from crc.api.common import ApiError
from crc.models.api_models import Task, MultiInstanceType, NavigationItem, NavigationItemSchema, WorkflowApi
from crc.models.file import LookupDataModel
from crc.models.task_event import TaskEventModel
from crc.models.study import StudyModel
from crc.models.user import UserModel
from crc.models.workflow import WorkflowModel, WorkflowStatus, WorkflowSpecModel
from crc.services.file_service import FileService
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

    @staticmethod
    def make_test_workflow(spec_id):
        user = db.session.query(UserModel).filter_by(uid="test").first()
        if not user:
            db.session.add(UserModel(uid="test"))
        study = db.session.query(StudyModel).filter_by(user_uid="test").first()
        if not study:
            db.session.add(StudyModel(user_uid="test", title="test"))
            db.session.commit()
        workflow_model = WorkflowModel(status=WorkflowStatus.not_started,
                                       workflow_spec_id=spec_id,
                                       last_updated=datetime.now(),
                                       study=study)
        return workflow_model

    @staticmethod
    def delete_test_data():
        for study in db.session.query(StudyModel).filter(StudyModel.user_uid == "test"):
            StudyService.delete_study(study.id)
            db.session.commit()

        user = db.session.query(UserModel).filter_by(uid="test").first()
        if user:
            db.session.delete(user)

    @staticmethod
    def test_spec(spec_id, required_only=False):
        """Runs a spec through it's paces to see if it results in any errors.
          Not fool-proof, but a good sanity check.  Returns the final data
          output form the last task if successful.

          required_only can be set to true, in which case this will run the
          spec, only completing the required fields, rather than everything.
          """

        workflow_model = WorkflowService.make_test_workflow(spec_id)

        try:
            processor = WorkflowProcessor(workflow_model, validate_only=True)
        except WorkflowException as we:
            WorkflowService.delete_test_data()
            raise ApiError.from_workflow_exception("workflow_validation_exception", str(we), we)

        while not processor.bpmn_workflow.is_completed():
            try:
                processor.bpmn_workflow.do_engine_steps()
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
                    WorkflowService.populate_form_with_random_data(task, task_api, required_only)
                    processor.complete_task(task)
            except WorkflowException as we:
                WorkflowService.delete_test_data()
                raise ApiError.from_workflow_exception("workflow_validation_exception", str(we), we)

        WorkflowService.delete_test_data()
        return processor.bpmn_workflow.last_task.data

    @staticmethod
    def populate_form_with_random_data(task, task_api, required_only):
        """populates a task with random data - useful for testing a spec."""

        if not hasattr(task.task_spec, 'form'): return

        form_data = task.data # Just like with the front end, we start with what was already there, and modify it.
        for field in task_api.form.fields:
            if required_only and (not field.has_validation(Task.VALIDATION_REQUIRED) or
                                  field.get_validation(Task.VALIDATION_REQUIRED).lower().strip() != "true"):
                continue # Don't include any fields that aren't specifically marked as required.
            if field.has_property("read_only") and field.get_property("read_only").lower().strip() == "true":
                continue # Don't mess about with read only fields.
            if field.has_property(Task.PROP_OPTIONS_REPEAT):
                group = field.get_property(Task.PROP_OPTIONS_REPEAT)
                if group not in form_data:
                    form_data[group] = [{},{},{}]
                for i in range(3):
                    form_data[group][i][field.id] = WorkflowService.get_random_data_for_field(field, task)
            else:
                form_data[field.id] = WorkflowService.get_random_data_for_field(field, task)
        if task.data is None:
            task.data = {}
        task.data.update(form_data)

    @staticmethod
    def get_random_data_for_field(field, task):
        has_ldap_lookup = field.has_property(Task.PROP_LDAP_LOOKUP)
        has_file_lookup = field.has_property(Task.PROP_OPTIONS_FILE_NAME)
        has_data_lookup = field.has_property(Task.PROP_OPTIONS_DATA_NAME)
        has_lookup = has_ldap_lookup or has_file_lookup or has_data_lookup

        if field.type == "enum" and not has_lookup:
            # If it's a normal enum field with no lookup,
            # return a random option.
            if len(field.options) > 0:
                random_choice = random.choice(field.options)
                if isinstance(random_choice, dict):
                    return {
                        'value': random_choice['id'],
                        'label': random_choice['name']
                    }
                else:
                    # fixme: why it is sometimes an EnumFormFieldOption, and other times not?
                    # Assume it is an EnumFormFieldOption
                    return {
                        'value': random_choice.id,
                        'label': random_choice.name
                    }
            else:
                raise ApiError.from_task("invalid_enum", "You specified an enumeration field (%s),"
                                                         " with no options" % field.id, task)
        elif field.type == "autocomplete" or field.type == "enum":
            # If it has a lookup, get the lookup model from the spreadsheet or task data, then return a random option
            # from the lookup model
            lookup_model = LookupService.get_lookup_model(task, field)
            if has_ldap_lookup:  # All ldap records get the same person.
                return {
                        "label": "dhf8r",
                        "value": "Dan Funk",
                        "data": {
                            "uid": "dhf8r",
                            "display_name": "Dan Funk",
                            "given_name": "Dan",
                            "email_address": "dhf8r@virginia.edu",
                            "department": "Depertment of Psychocosmographictology",
                            "affiliation": "Rousabout",
                            "sponsor_type": "Staff"}
                        }
            elif lookup_model:
                data = db.session.query(LookupDataModel).filter(
                    LookupDataModel.lookup_file_model == lookup_model).limit(10).all()
                options = [{"value": d.value, "label": d.label, "data": d.data} for d in data]
                return random.choice(options)
            else:
                raise ApiError.from_task("unknown_lookup_option", "The settings for this auto complete field "
                                                                 "are incorrect: %s " % field.id, task)
        elif field.type == "long":
            return random.randint(1, 1000)
        elif field.type == 'boolean':
            return random.choice([True, False])
        elif field.type == 'file':
            # fixme: produce some something sensible for files.
            return random.randint(1, 100)
            # fixme: produce some something sensible for files.
        elif field.type == 'files':
            return random.randrange(1, 100)
        else:
            return WorkflowService._random_string()

    def __get_options(self):
        pass

    @staticmethod
    def _random_string(string_length=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(string_length))

    @staticmethod
    def processor_to_workflow_api(processor: WorkflowProcessor, next_task=None):
        """Returns an API model representing the state of the current workflow, if requested, and
        possible, next_task is set to the current_task."""

        nav_dict = processor.bpmn_workflow.get_nav_list()

        # Some basic cleanup of the title for the for the navigation.
        navigation = []
        for nav_item in nav_dict:
            spiff_task = processor.bpmn_workflow.get_task(nav_item['task_id'])
            if 'description' in nav_item:
                nav_item['title'] = nav_item.pop('description')
                # fixme: duplicate code from the workflow_service. Should only do this in one place.
                if nav_item['title'] is not None and ' ' in nav_item['title']:
                    nav_item['title'] = nav_item['title'].partition(' ')[2]
            else:
                nav_item['title'] = ""
            if spiff_task:
                nav_item['task'] = WorkflowService.spiff_task_to_api_task(spiff_task, add_docs_and_forms=False)
                nav_item['title'] = nav_item['task'].title  # Prefer the task title.

                user_uids = WorkflowService.get_users_assigned_to_task(processor, spiff_task)
                if not UserService.in_list(user_uids, allow_admin_impersonate=True):
                    nav_item['state'] = WorkflowService.TASK_STATE_LOCKED

            else:
                nav_item['task'] = None


            navigation.append(NavigationItem(**nav_item))
            NavigationItemSchema().dump(nav_item)

        spec = db.session.query(WorkflowSpecModel).filter_by(id=processor.workflow_spec_id).first()
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
            title=spec.display_name
        )
        if not next_task:  # The Next Task can be requested to be a certain task, useful for parallel tasks.
            # This may or may not work, sometimes there is no next task to complete.
            next_task = processor.next_task()
        if next_task:
            previous_form_data = WorkflowService.get_previously_submitted_data(processor.workflow_model.id, next_task)
            DeepMerge.merge(next_task.data, previous_form_data)
            workflow_api.next_task = WorkflowService.spiff_task_to_api_task(next_task, add_docs_and_forms=True)
            # Update the state of the task to locked if the current user does not own the task.
            user_uids = WorkflowService.get_users_assigned_to_task(processor, next_task)
            if not UserService.in_list(user_uids, allow_admin_impersonate=True):
                workflow_api.next_task.state = WorkflowService.TASK_STATE_LOCKED
        return workflow_api

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
                task.title = spiff_task.workflow.script_engine.evaluate_expression(spiff_task, task.properties[Task.PROP_EXTENSIONS_TITLE])
            except Exception as e:
                raise ApiError.from_task(code="task_title_error", message="Could not set task title on task %s with '%s' property because %s" %
                                                              (spiff_task.task_spec.name, Task.PROP_EXTENSIONS_TITLE, str(e)), task=spiff_task)
        elif task.title and ' ' in task.title:
            task.title = task.title.partition(' ')[2]
        return task

    @staticmethod
    def _process_properties(spiff_task, props):
        """Runs all the property values through the Jinja2 processor to inject data."""
        for k, v in props.items():
            try:
                template = Template(v)
                props[k] = template.render(**spiff_task.data)
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
            template = Template(raw_doc)
            return template.render(**spiff_task.data)
        except jinja2.exceptions.TemplateError as ue:
            raise ApiError.from_task(code="template_error", message="Error processing template for task %s: %s" %
                                                          (spiff_task.task_spec.name, str(ue)), task=spiff_task)
        except TypeError as te:
            raise ApiError.from_task(code="template_error", message="Error processing template for task %s: %s" %
                                                          (spiff_task.task_spec.name, str(te)), task=spiff_task)
        except Exception as e:
            app.logger.error(str(e), exc_info=True)

    @staticmethod
    def process_options(spiff_task, field):

        # If this is an auto-complete field, do not populate options, a lookup will happen later.
        if field.type == Task.FIELD_TYPE_AUTO_COMPLETE:
            pass
        elif field.has_property(Task.PROP_OPTIONS_FILE_NAME):
            lookup_model = LookupService.get_lookup_model(spiff_task, field)
            data = db.session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_model).all()
            if not hasattr(field, 'options'):
                field.options = []
            for d in data:
                field.options.append({"id": d.value, "name": d.label, "data": d.data})
        elif field.has_property(Task.PROP_OPTIONS_DATA_NAME):
            field.options = WorkflowService.get_options_from_task_data(spiff_task, field)
        return field

    @staticmethod
    def get_options_from_task_data(spiff_task, field):
        if not (field.has_property(Task.PROP_OPTIONS_DATA_VALUE_COLUMN) or
                field.has_property(Task.PROP_OPTIONS_DATA_LABEL_COLUMN)):
            raise ApiError.from_task("invalid_enum",
                                     f"For enumerations based on task data, you must include 3 properties: "
                                     f"{Task.PROP_OPTIONS_DATA_NAME}, {Task.PROP_OPTIONS_DATA_VALUE_COLUMN}, "
                                     f"{Task.PROP_OPTIONS_DATA_LABEL_COLUMN}", task=spiff_task)
        prop = field.get_property(Task.PROP_OPTIONS_DATA_NAME)
        if prop not in spiff_task.data:
            raise ApiError.from_task("invalid_enum", f"For enumerations based on task data, task data must have "
                                                     f"a property called {prop}", task=spiff_task)
        # Get the enum options from the task data
        data_model = spiff_task.data[prop]
        value_column = field.get_property(Task.PROP_OPTIONS_DATA_VALUE_COLUMN)
        label_column = field.get_property(Task.PROP_OPTIONS_DATA_LABEL_COLUMN)
        items = data_model.items() if isinstance(data_model, dict) else data_model
        options = []
        for item in items:
            options.append({"id": item[value_column], "name": item[label_column], "data": item})
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
    def get_users_assigned_to_task(processor, spiff_task):
        if not hasattr(spiff_task.task_spec, 'lane') or spiff_task.task_spec.lane is None:
            return [processor.workflow_model.study.user_uid]
            # todo: return a list of all users that can edit the study by default
        if spiff_task.task_spec.lane not in spiff_task.data:
            return []  # No users are assignable to the task at this moment
        lane_users = spiff_task.data[spiff_task.task_spec.lane]
        if not isinstance(lane_users, list):
            lane_users = [lane_users]
        return lane_users

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
            date=datetime.now(),
        )
        db.session.add(task_event)
        db.session.commit()

    @staticmethod
    def extract_form_data(latest_data, task):
        """Removes data from latest_data that would be added by the child task or any of its children."""
        data = {}

        if hasattr(task.task_spec, 'form'):
            for field in task.task_spec.form.fields:
                if field.has_property(Task.PROP_OPTIONS_READ_ONLY) and \
                        field.get_property(Task.PROP_OPTIONS_READ_ONLY).lower().strip() == "true":
                    continue  # Don't add read-only data
                elif field.has_property(Task.PROP_OPTIONS_REPEAT):
                    group = field.get_property(Task.PROP_OPTIONS_REPEAT)
                    if group in latest_data:
                        data[group] = latest_data[group]
                elif isinstance(task.task_spec, MultiInstanceTask):
                    group = task.task_spec.elementVar
                    if group in latest_data:
                        data[group] = latest_data[group]
                else:
                    if field.id in latest_data:
                        data[field.id] = latest_data[field.id]

        return data



