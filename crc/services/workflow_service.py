import string
from datetime import datetime
import random

import jinja2
from SpiffWorkflow import Task as SpiffTask, WorkflowException
from SpiffWorkflow.bpmn.specs.ManualTask import ManualTask
from SpiffWorkflow.bpmn.specs.ScriptTask import ScriptTask
from SpiffWorkflow.bpmn.specs.UserTask import UserTask
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.dmn.specs.BusinessRuleTask import BusinessRuleTask
from SpiffWorkflow.specs import CancelTask, StartTask
from flask import g
from jinja2 import Template

from crc import db, app
from crc.api.common import ApiError
from crc.models.api_models import Task, MultiInstanceType
from crc.models.file import LookupDataModel
from crc.models.stats import TaskEventModel
from crc.services.file_service import FileService
from crc.services.lookup_service import LookupService
from crc.services.workflow_processor import WorkflowProcessor, CustomBpmnScriptEngine


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
     own API models with additional information and capabilities."""

    @classmethod
    def test_spec(cls, spec_id):
        """Runs a spec through it's paces to see if it results in any errors.  Not fool-proof, but a good
        sanity check."""
        version = WorkflowProcessor.get_latest_version_string(spec_id)
        spec = WorkflowProcessor.get_spec(spec_id, version)
        bpmn_workflow = BpmnWorkflow(spec, script_engine=CustomBpmnScriptEngine())
        bpmn_workflow.data[WorkflowProcessor.STUDY_ID_KEY] = 1
        bpmn_workflow.data[WorkflowProcessor.WORKFLOW_ID_KEY] = spec_id
        bpmn_workflow.data[WorkflowProcessor.VALIDATION_PROCESS_KEY] = True

        while not bpmn_workflow.is_completed():
            try:
                bpmn_workflow.do_engine_steps()
                tasks = bpmn_workflow.get_tasks(SpiffTask.READY)
                for task in tasks:
                    task_api = WorkflowService.spiff_task_to_api_task(
                        task,
                        add_docs_and_forms=True)  # Assure we try to process the documenation, and raise those errors.
                    WorkflowService.populate_form_with_random_data(task, task_api)
                    task.complete()
            except WorkflowException as we:
                raise ApiError.from_task_spec("workflow_execution_exception", str(we),
                                              we.sender)

    @staticmethod
    def populate_form_with_random_data(task, task_api):
        """populates a task with random data - useful for testing a spec."""

        if not hasattr(task.task_spec, 'form'): return

        form_data = {}
        for field in task_api.form.fields:
            if field.type == "enum":
                if len(field.options) > 0:
                    random_choice = random.choice(field.options)
                    if isinstance(random_choice, dict):
                        form_data[field.id] = random.choice(field.options)['id']
                    else:
                        # fixme: why it is sometimes an EnumFormFieldOption, and other times not?
                        form_data[field.id] = random_choice.id ## Assume it is an EnumFormFieldOption
                else:
                    raise ApiError.from_task("invalid_enum", "You specified an enumeration field (%s),"
                                                             " with no options" % field.id,
                                             task)
            elif field.type == "autocomplete":
                lookup_model = LookupService.get_lookup_table(task, field)
                if field.has_property(Task.PROP_LDAP_LOOKUP):
                    form_data[field.id] = {
                        "label": "dhf8r",
                        "value": "Dan Funk",
                        "data": {
                            "uid": "dhf8r",
                            "display_name": "Dan Funk",
                            "given_name": "Dan",
                            "email_address": "dhf8r@virginia.edu",
                            "department": "Depertment of Psychocosmographictology",
                            "affiliation": "Rousabout",
                            "sponsor_type": "Staff"
                        }
                    }
                elif lookup_model:
                    data = db.session.query(LookupDataModel).filter(
                        LookupDataModel.lookup_file_model == lookup_model).limit(10).all()
                    options = []
                    for d in data:
                        options.append({"id": d.value, "name": d.label})
                    form_data[field.id] = random.choice(options)
                else:
                    raise ApiError.from_task("invalid_autocomplete", "The settings for this auto complete field "
                                                                     "are incorrect: %s " % field.id, task)
            elif field.type == "long":
                form_data[field.id] = random.randint(1, 1000)
            elif field.type == 'boolean':
                form_data[field.id] = random.choice([True, False])
            elif field.type == 'file':
                form_data[field.id] = random.randint(1, 100)
            elif field.type == 'files':
                form_data[field.id] = random.randrange(1, 100)
            else:
                form_data[field.id] = WorkflowService._random_string()
        if task.data is None:
            task.data = {}
        task.data.update(form_data)

    def __get_options(self):
        pass


    @staticmethod
    def _random_string(string_length=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(string_length))

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

            #            return "Error processing template. %s" % ue.message
            raise ApiError(code="template_error", message="Error processing template for task %s: %s" %
                                                          (spiff_task.task_spec.name, str(ue)), status_code=500)
        # TODO:  Catch additional errors and report back.

    @staticmethod
    def process_options(spiff_task, field):
        lookup_model = LookupService.get_lookup_table(spiff_task, field)

        # If this is an auto-complete field, do not populate options, a lookup will happen later.
        if field.type == Task.FIELD_TYPE_AUTO_COMPLETE:
            pass
        else:
            data = db.session.query(LookupDataModel).filter(LookupDataModel.lookup_file_model == lookup_model).all()
            if not hasattr(field, 'options'):
                field.options = []
            for d in data:
                field.options.append({"id": d.value, "name": d.label})

    @staticmethod
    def log_task_action(processor, spiff_task, action):
        task = WorkflowService.spiff_task_to_api_task(spiff_task)
        workflow_model = processor.workflow_model
        task_event = TaskEventModel(
            study_id=workflow_model.study_id,
            user_uid=g.user.uid,
            workflow_id=workflow_model.id,
            workflow_spec_id=workflow_model.workflow_spec_id,
            spec_version=workflow_model.spec_version,
            action=action,
            task_id=task.id,
            task_name=task.name,
            task_title=task.title,
            task_type=str(task.type),
            task_state=task.state,
            mi_type=task.multi_instance_type.value,  # Some tasks have a repeat behavior.
            mi_count=task.multi_instance_count,  # This is the number of times the task could repeat.
            mi_index=task.multi_instance_index,  # And the index of the currently repeating task.
            process_name=task.process_name,
            date=datetime.now(),
        )
        db.session.add(task_event)
        db.session.commit()
