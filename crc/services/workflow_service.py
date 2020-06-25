import copy
import string
from datetime import datetime
import random

import jinja2
from SpiffWorkflow import Task as SpiffTask, WorkflowException
from SpiffWorkflow.bpmn.specs.ManualTask import ManualTask
from SpiffWorkflow.bpmn.specs.MultiInstanceTask import MultiInstanceTask
from SpiffWorkflow.bpmn.specs.ScriptTask import ScriptTask
from SpiffWorkflow.bpmn.specs.UserTask import UserTask
from SpiffWorkflow.dmn.specs.BusinessRuleTask import BusinessRuleTask
from SpiffWorkflow.specs import CancelTask, StartTask
from SpiffWorkflow.util.deep_merge import DeepMerge
from jinja2 import Template

from crc import db, app
from crc.api.common import ApiError
from crc.models.api_models import Task, MultiInstanceType, NavigationItem, NavigationItemSchema, WorkflowApi
from crc.models.file import LookupDataModel
from crc.models.stats import TaskEventModel
from crc.models.study import StudyModel
from crc.models.user import UserModel
from crc.models.workflow import WorkflowModel, WorkflowStatus, WorkflowSpecModel
from crc.services.file_service import FileService
from crc.services.lookup_service import LookupService
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor


class WorkflowService(object):
    TASK_ACTION_COMPLETE = "Complete"
    TASK_ACTION_TOKEN_RESET = "Backwards Move"
    TASK_ACTION_HARD_RESET = "Restart (Hard)"
    TASK_ACTION_SOFT_RESET = "Restart (Soft)"

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
                    task_api = WorkflowService.spiff_task_to_api_task(
                        task,
                        add_docs_and_forms=True)  # Assure we try to process the documenation, and raise those errors.
                    WorkflowService.populate_form_with_random_data(task, task_api, required_only)
                    task.complete()
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
        if field.type == "enum":
            if len(field.options) > 0:
                random_choice = random.choice(field.options)
                if isinstance(random_choice, dict):
                    return random.choice(field.options)['id']
                else:
                    # fixme: why it is sometimes an EnumFormFieldOption, and other times not?
                    return random_choice.id  ## Assume it is an EnumFormFieldOption
            else:
                raise ApiError.from_task("invalid_enum", "You specified an enumeration field (%s),"
                                                         " with no options" % field.id, task)
        elif field.type == "autocomplete":
            lookup_model = LookupService.get_lookup_model(task, field)
            if field.has_property(Task.PROP_LDAP_LOOKUP):  # All ldap records get the same person.
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
                options = []
                for d in data:
                    options.append({"id": d.value, "label": d.label})
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
        navigation = []
        for nav_item in nav_dict:
            spiff_task = processor.bpmn_workflow.get_task(nav_item['task_id'])
            if 'description' in nav_item:
                nav_item['title'] = nav_item.pop('description')
                # fixme: duplicate code from the workflow_service. Should only do this in one place.
                if ' ' in nav_item['title']:
                    nav_item['title'] = nav_item['title'].partition(' ')[2]
            else:
                nav_item['title'] = ""
            if spiff_task:
                nav_item['task'] = WorkflowService.spiff_task_to_api_task(spiff_task, add_docs_and_forms=False)
                nav_item['title'] = nav_item['task'].title  # Prefer the task title.
            else:
                nav_item['task'] = None
            if not 'is_decision' in nav_item:
                nav_item['is_decision'] = False

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

        return workflow_api

    @staticmethod
    def get_previously_submitted_data(workflow_id, task):
        """ If the user has completed this task previously, find the form data for the last submission."""
        latest_event = db.session.query(TaskEventModel) \
            .filter_by(workflow_id=workflow_id) \
            .filter_by(task_name=task.task_spec.name) \
            .filter_by(action=WorkflowService.TASK_ACTION_COMPLETE) \
            .order_by(TaskEventModel.date.desc()).first()
        if latest_event:
            if latest_event.form_data is not None:
                return latest_event.form_data
            else:
                app.logger.error("missing_form_dat", "We have lost data for workflow %i, task %s, it is not "
                                                      "in the task event model, "
                                                      "and it should be." % (workflow_id, task.task_spec.name))
                return {}
        else:
            return {}


    @staticmethod
    def spiff_task_to_api_task(spiff_task, add_docs_and_forms=False):
        task_type = spiff_task.task_spec.__class__.__name__

        if isinstance(spiff_task.task_spec, UserTask):
            task_type = "UserTask"
        elif isinstance(spiff_task.task_spec, ManualTask):
            task_type = "ManualTask"
        elif isinstance(spiff_task.task_spec, BusinessRuleTask):
            task_type = "BusinessRuleTask"
        elif isinstance(spiff_task.task_spec, CancelTask):
            task_type = "CancelTask"
        elif isinstance(spiff_task.task_spec, ScriptTask):
            task_type = "ScriptTask"
        elif isinstance(spiff_task.task_spec, StartTask):
            task_type = "StartTask"
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
            for id, val in spiff_task.task_spec.extensions.items():
                props[id] = val

        task = Task(spiff_task.id,
                    spiff_task.task_spec.name,
                    spiff_task.task_spec.description,
                    task_type,
                    spiff_task.get_state_name(),
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
                for field in task.form.fields:
                    WorkflowService.process_options(spiff_task, field)
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
            task.title = task.properties['display_name']
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
                app.logger.error("Failed to process task property %s " % str(ue))
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
        # TODO:  Catch additional errors and report back.

    @staticmethod
    def process_options(spiff_task, field):

        # If this is an auto-complete field, do not populate options, a lookup will happen later.
        if field.type == Task.FIELD_TYPE_AUTO_COMPLETE:
            pass
        elif field.has_property(Task.PROP_OPTIONS_FILE):
            lookup_model = LookupService.get_lookup_model(spiff_task, field)
            data = db.session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_model).all()
            if not hasattr(field, 'options'):
                field.options = []
            for d in data:
                field.options.append({"id": d.value, "name": d.label})

    @staticmethod
    def log_task_action(user_uid, workflow_model, spiff_task, action, version):
        task = WorkflowService.spiff_task_to_api_task(spiff_task)
        form_data = WorkflowService.extract_form_data(spiff_task.data, spiff_task)
        task_event = TaskEventModel(
            study_id=workflow_model.study_id,
            user_uid=user_uid,
            workflow_id=workflow_model.id,
            workflow_spec_id=workflow_model.workflow_spec_id,
            spec_version=version,
            action=action,
            task_id=task.id,
            task_name=task.name,
            task_title=task.title,
            task_type=str(task.type),
            task_state=task.state,
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
    def fix_legacy_data_model_for_rrt():
        """  Remove this after use!  This is just to fix RRT so the data is handled correctly.

        Utility that is likely called via the flask command line, it will loop through all the
        workflows in the system and attempt to add the right data into the task action log so that
        users do not have to re fill out all of the forms if they start over or go back in the workflow.
        Viciously inefficient, but should only have to run one time for RRT"""
        workflows = db.session.query(WorkflowModel).all()
        for workflow_model in workflows:
            task_logs = db.session.query(TaskEventModel) \
                .filter(TaskEventModel.workflow_id == workflow_model.id) \
                .filter(TaskEventModel.action == WorkflowService.TASK_ACTION_COMPLETE) \
                .order_by(TaskEventModel.date.desc()).all()

            processor = WorkflowProcessor(workflow_model)
            # Grab all the data from last task completed, which will be everything in this
            # rrt situation because of how we were keeping all the data at the time.
            latest_data = processor.next_task().data

            # Move forward in the task spec tree, dropping any data that would have been
            # added in subsequent tasks, just looking at form data, will not track the automated
            # task data additions, hopefully this doesn't hang us.
            for log in task_logs:
#                if log.task_data is not None:  # Only do this if the task event does not have data populated in it.
#                    continue
                data = copy.deepcopy(latest_data) # Or you end up with insane crazy issues.
                # In the simple case of RRT, there is exactly one task for the given task_spec
                task = processor.bpmn_workflow.get_tasks_from_spec_name(log.task_name)[0]
                data = WorkflowService.extract_form_data(data, task)
                log.form_data = data
                db.session.add(log)

        db.session.commit()

    @staticmethod
    def extract_form_data(latest_data, task):
        """Removes data from latest_data that would be added by the child task or any of it's children."""
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



