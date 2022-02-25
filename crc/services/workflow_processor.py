from typing import List

from SpiffWorkflow.bpmn.PythonScriptEngine import PythonScriptEngine
from SpiffWorkflow.bpmn.specs.events import EndEvent, CancelEventDefinition
from SpiffWorkflow.serializer.exceptions import MissingSpecError
from SpiffWorkflow.util.metrics import timeit, firsttime, sincetime
from lxml import etree
from datetime import datetime

from SpiffWorkflow import Task as SpiffTask, WorkflowException, Task
from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from SpiffWorkflow.bpmn.serializer.BpmnSerializer import BpmnSerializer
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.camunda.parser.CamundaParser import CamundaParser
from SpiffWorkflow.dmn.parser.BpmnDmnParser import BpmnDmnParser
from SpiffWorkflow.exceptions import WorkflowTaskExecException
from SpiffWorkflow.specs import WorkflowSpec

from crc import session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileType, File
from crc.models.task_event import TaskEventModel
from crc.models.user import UserModelSchema
from crc.models.workflow import WorkflowStatus, WorkflowModel, WorkflowSpecInfo
from crc.scripts.script import Script
from crc import app
from crc.services.spec_file_service import SpecFileService
from crc.services.user_file_service import UserFileService
from crc.services.user_service import UserService
from crc.services.workflow_spec_service import WorkflowSpecService


class CustomBpmnScriptEngine(PythonScriptEngine):
    """This is a custom script processor that can be easily injected into Spiff Workflow.
    It will execute python code read in from the bpmn.  It will also make any scripts in the
     scripts directory available for execution. """

    @timeit
    def evaluate(self, task, expression):
        """
        Evaluate the given expression, within the context of the given task and
        return the result.
        """
        study_id = task.workflow.data[WorkflowProcessor.STUDY_ID_KEY]
        if WorkflowProcessor.WORKFLOW_ID_KEY in task.workflow.data:
            workflow_id = task.workflow.data[WorkflowProcessor.WORKFLOW_ID_KEY]
        else:
            workflow_id = None

        try:
            if task.workflow.data[WorkflowProcessor.VALIDATION_PROCESS_KEY]:
                augmentMethods = Script.generate_augmented_validate_list(task, study_id, workflow_id)
            else:
                augmentMethods = Script.generate_augmented_list(task, study_id, workflow_id)

            return self._evaluate(expression, external_methods=augmentMethods, **task.data)

        except Exception as e:
            raise WorkflowTaskExecException(task,
                                            "Error evaluating expression "
                                            "'%s', %s" % (expression, str(e)))

    @timeit
    def execute(self, task: SpiffTask, script, data):
        study_id = task.workflow.data[WorkflowProcessor.STUDY_ID_KEY]
        if WorkflowProcessor.WORKFLOW_ID_KEY in task.workflow.data:
            workflow_id = task.workflow.data[WorkflowProcessor.WORKFLOW_ID_KEY]
        else:
            workflow_id = None
        try:
            if task.workflow.data[WorkflowProcessor.VALIDATION_PROCESS_KEY]:
                augment_methods = Script.generate_augmented_validate_list(task, study_id, workflow_id)
            else:
                # Costs 0.25 seconds the first time it is executed.
                augment_methods = Script.generate_augmented_list(task, study_id, workflow_id)
            super().execute(task, script, data, external_methods=augment_methods)
        except WorkflowException as e:
            raise e
        except Exception as e:
            raise WorkflowTaskExecException(task, f' {script}, {e}', e)


class MyCustomParser(BpmnDmnParser):
    """
    A BPMN and DMN parser that can also parse Camunda forms.
    """
    OVERRIDE_PARSER_CLASSES = BpmnDmnParser.OVERRIDE_PARSER_CLASSES
    OVERRIDE_PARSER_CLASSES.update(CamundaParser.OVERRIDE_PARSER_CLASSES)


class WorkflowProcessor(object):
    _script_engine = CustomBpmnScriptEngine()
    _serializer = BpmnSerializer()

    WORKFLOW_ID_KEY = "workflow_id"
    STUDY_ID_KEY = "study_id"
    VALIDATION_PROCESS_KEY = "validate_only"

    def __init__(self, workflow_model: WorkflowModel, validate_only=False):
        """Create a Workflow Processor based on the serialized information available in the workflow model."""

        self.workflow_model = workflow_model
        self.workflow_spec_service = WorkflowSpecService()
        spec = None
        if workflow_model.bpmn_workflow_json is None:
            spec_info = self.workflow_spec_service.get_spec(workflow_model.workflow_spec_id)
            if spec_info is None:
                raise (ApiError("missing_spec", "The spec this workflow references does not currently exist."))
            self.spec_files = SpecFileService.get_files(spec_info, include_libraries=True)
            spec = self.get_spec(self.spec_files, spec_info)

        self.workflow_spec_id = workflow_model.workflow_spec_id

        try:
            self.bpmn_workflow = self.__get_bpmn_workflow(workflow_model, spec, validate_only)
            self.bpmn_workflow.script_engine = self._script_engine

            if UserService.has_user():
                current_user = UserService.current_user(allow_admin_impersonate=True)
                current_user_data = UserModelSchema().dump(current_user)
                tasks = self.bpmn_workflow.get_tasks(SpiffTask.READY)
                for task in tasks:
                    task.data['current_user'] = current_user_data

            if self.WORKFLOW_ID_KEY not in self.bpmn_workflow.data:
                if not workflow_model.id:
                    session.add(workflow_model)
                    # If the model is new, and has no id, save it, write it into the workflow model
                    # and save it again.  In this way, the workflow process is always aware of the
                    # database model to which it is associated, and scripts running within the model
                    # can then load data as needed.
                self.bpmn_workflow.data[WorkflowProcessor.WORKFLOW_ID_KEY] = workflow_model.id
                workflow_model.bpmn_workflow_json = WorkflowProcessor._serializer.serialize_workflow(
                    self.bpmn_workflow, include_spec=True)

                self.save()

        except MissingSpecError as ke:
            raise ApiError(code="unexpected_workflow_structure",
                           message="Failed to deserialize workflow"
                                   " '%s'  due to a mis-placed or missing task '%s'" %
                                   (self.workflow_spec_id, str(ke)))

    @staticmethod
    @timeit
    def reset(workflow_model, clear_data=False, delete_files=False):
        # Try to execute a cancel notify
        try:
            bpmn_workflow = WorkflowProcessor.__get_bpmn_workflow(workflow_model)
            WorkflowProcessor.__cancel_notify(bpmn_workflow)
        except Exception as e:
            app.logger.error(f"Unable to send a cancel notify for workflow %s during a reset."
                             f" Continuing with the reset anyway so we don't get in an unresolvable"
                             f" state. An %s error occured with the following information: %s" %
                             (workflow_model.id, e.__class__.__name__, str(e)))
        workflow_model.bpmn_workflow_json = None
        if clear_data:
            # Clear form_data from task_events
            task_events = session.query(TaskEventModel). \
                filter(TaskEventModel.workflow_id == workflow_model.id).all()
            for task_event in task_events:
                task_event.form_data = {}
                session.add(task_event)
        if delete_files:
            files = FileModel.query.filter(FileModel.workflow_id == workflow_model.id).all()
            for file in files:
                UserFileService.delete_file(file.id)
        session.commit()
        return WorkflowProcessor(workflow_model)

    @staticmethod
    @timeit
    def __get_bpmn_workflow(workflow_model: WorkflowModel, spec: WorkflowSpec = None, validate_only=False):
        if workflow_model.bpmn_workflow_json:
            bpmn_workflow = WorkflowProcessor._serializer.deserialize_workflow(workflow_model.bpmn_workflow_json,
                                                                  workflow_spec=spec)
            bpmn_workflow.script_engine = WorkflowProcessor._script_engine
        else:
            bpmn_workflow = BpmnWorkflow(spec, script_engine=WorkflowProcessor._script_engine)
            bpmn_workflow.data[WorkflowProcessor.STUDY_ID_KEY] = workflow_model.study_id
            bpmn_workflow.data[WorkflowProcessor.VALIDATION_PROCESS_KEY] = validate_only
        return bpmn_workflow

    def save(self):
        """Saves the current state of this processor to the database """
        self.workflow_model.bpmn_workflow_json = self.serialize()
        complete_states = [SpiffTask.CANCELLED, SpiffTask.COMPLETED]
        tasks = list(self.get_all_user_tasks())
        self.workflow_model.status = self.get_status()
        self.workflow_model.total_tasks = len(tasks)
        self.workflow_model.completed_tasks = sum(1 for t in tasks if t.state in complete_states)
        self.workflow_model.last_updated = datetime.utcnow()
        session.add(self.workflow_model)
        session.commit()

    @staticmethod
    @timeit
    def run_master_spec(spec_model, study):
        """Executes a BPMN specification for the given study, without recording any information to the database
        Useful for running the master specification, which should not persist. """
        spec_files = SpecFileService().get_files(spec_model, include_libraries=True)
        spec = WorkflowProcessor.get_spec(spec_files, spec_model)
        try:
            bpmn_workflow = BpmnWorkflow(spec, script_engine=WorkflowProcessor._script_engine)
            bpmn_workflow.data[WorkflowProcessor.STUDY_ID_KEY] = study.id
            bpmn_workflow.data[WorkflowProcessor.VALIDATION_PROCESS_KEY] = False
            bpmn_workflow.do_engine_steps()
        except WorkflowException as we:
            raise ApiError.from_task_spec("error_running_master_spec", str(we), we.sender)

        if not bpmn_workflow.is_completed():
            raise ApiError("master_spec_not_automatic",
                           "The master spec should only contain fully automated tasks, it failed to complete.")

        return bpmn_workflow.last_task.data

    @staticmethod
    def get_parser():
        parser = MyCustomParser()
        return parser

    @staticmethod
    def get_spec(files: List[File], workflow_spec_info: WorkflowSpecInfo):
        """Returns a SpiffWorkflow specification for the given workflow spec,
        using the files provided. """
        parser = WorkflowProcessor.get_parser()

        for file in files:
            data = SpecFileService.get_data(workflow_spec_info, file.name)
            if file.type == FileType.bpmn:
                bpmn: etree.Element = etree.fromstring(data)
                parser.add_bpmn_xml(bpmn, filename=file.name)
            elif file.type == FileType.dmn:
                dmn: etree.Element = etree.fromstring(data)
                parser.add_dmn_xml(dmn, filename=file.name)
        if workflow_spec_info.primary_process_id is None or workflow_spec_info.primary_process_id == "":
            raise (ApiError(code="no_primary_bpmn_error",
                            message="There is no primary BPMN model defined for workflow %s" % workflow_spec_info.id))
        try:
            spec = parser.get_spec(workflow_spec_info.primary_process_id)
        except ValidationException as ve:
            raise ApiError(code="workflow_validation_error",
                           message="Failed to parse the Workflow Specification. " +
                                   "Error is '%s.'" % str(ve),
                           file_name=ve.filename,
                           task_id=ve.id,
                           tag=ve.tag)
        return spec

    @staticmethod
    def status_of(bpmn_workflow):
        if bpmn_workflow.is_completed():
            return WorkflowStatus.complete
        user_tasks = bpmn_workflow.get_ready_user_tasks()
        waiting_tasks = bpmn_workflow.get_tasks(Task.WAITING)
        if len(waiting_tasks) > 0:
            return WorkflowStatus.waiting
        if len(user_tasks) > 0:
            return WorkflowStatus.user_input_required
        else:
            return WorkflowStatus.waiting

    def get_status(self):
        return self.status_of(self.bpmn_workflow)

    def do_engine_steps(self, exit_at = None):
        try:
            self.bpmn_workflow.refresh_waiting_tasks()
            self.bpmn_workflow.do_engine_steps(exit_at = exit_at)
        except WorkflowTaskExecException as we:
            raise ApiError.from_workflow_exception("task_error", str(we), we)

    def cancel_notify(self):
        self.__cancel_notify(self.bpmn_workflow)

    @staticmethod
    def __cancel_notify(bpmn_workflow):
        try:
            # A little hackly, but make the bpmn_workflow catch a cancel event.
            bpmn_workflow.signal('cancel')  # generate a cancel signal.
            bpmn_workflow.catch(CancelEventDefinition())
            bpmn_workflow.do_engine_steps()
        except WorkflowTaskExecException as we:
            raise ApiError.from_workflow_exception("task_error", str(we), we)


    def serialize(self):
        return self._serializer.serialize_workflow(self.bpmn_workflow,include_spec=True)

    def next_user_tasks(self):
        return self.bpmn_workflow.get_ready_user_tasks()

    def next_task(self):
        """Returns the next task that should be completed
        even if there are parallel tasks and multiple options are
        available.
        If the workflow is complete
        it will return the final end task.
        """

        # If the whole blessed mess is done, return the end_event task in the tree
        # This was failing in the case of a call activity where we have an intermediate EndEvent
        # what we really want is the LAST EndEvent

        endtasks = []
        if self.bpmn_workflow.is_completed():
            for task in SpiffTask.Iterator(self.bpmn_workflow.task_tree, SpiffTask.ANY_MASK):
                # Assure that we find the end event for this workflow, and not for any sub-workflows.
                if isinstance(task.task_spec, EndEvent) and task.workflow == self.bpmn_workflow:
                    endtasks.append(task)
            return endtasks[-1]

        # If there are ready tasks to complete, return the next ready task, but return the one
        # in the active parallel path if possible.  In some cases the active parallel path may itself be
        # a parallel gateway with multiple tasks, so prefer ones that share a parent.

        # Get a list of all ready tasks
        ready_tasks = self.bpmn_workflow.get_tasks(SpiffTask.READY)

        if len(ready_tasks) == 0:
            # If no ready tasks exist, check for a waiting task.
            waiting_tasks = self.bpmn_workflow.get_tasks(SpiffTask.WAITING)
            if len(waiting_tasks) > 0:
                return waiting_tasks[0]
            else:
                return  # We have not tasks to return.

        # Get a list of all completed user tasks (Non engine tasks)
        completed_user_tasks = self.completed_user_tasks()

        # If there are no completed user tasks, return the first ready task
        if len(completed_user_tasks) == 0:
            return ready_tasks[0]

        # Take the last completed task, find a child of it, and return that task
        last_user_task = completed_user_tasks[0]
        if len(ready_tasks) > 0:
            for task in ready_tasks:
                if task._is_descendant_of(last_user_task):
                    return task
            for task in ready_tasks:
                if self.bpmn_workflow.last_task and task.parent == last_user_task.parent:
                    return task

            return ready_tasks[0]

        # If there are no ready tasks, but the thing isn't complete yet, find the first non-complete task
        # and return that
        next_task = None
        for task in SpiffTask.Iterator(self.bpmn_workflow.task_tree, SpiffTask.NOT_FINISHED_MASK):
            next_task = task
        return next_task

    def completed_user_tasks(self):
        completed_user_tasks = self.bpmn_workflow.get_tasks(SpiffTask.COMPLETED)
        completed_user_tasks.reverse()
        completed_user_tasks = list(
        filter(lambda task: not self.bpmn_workflow._is_engine_task(task.task_spec), completed_user_tasks))
        return completed_user_tasks

    def previous_task(self):
        return None

    def complete_task(self, task):
        self.bpmn_workflow.complete_task_from_id(task.id)

    def get_data(self):
        return self.bpmn_workflow.data

    def get_workflow_id(self):
        return self.workflow_model.id

    def get_study_id(self):
        return self.bpmn_workflow.data[self.STUDY_ID_KEY]

    def get_ready_user_tasks(self):
        return self.bpmn_workflow.get_ready_user_tasks()

    def get_current_user_tasks(self):
        """Return a list of all user tasks that are READY or
        COMPLETE and are parallel to the READY Task."""
        ready_tasks = self.bpmn_workflow.get_ready_user_tasks()
        additional_tasks = []
        if len(ready_tasks) > 0:
            for child in ready_tasks[0].parent.children:
                if child.state == SpiffTask.COMPLETED:
                    additional_tasks.append(child)
        return ready_tasks + additional_tasks

    def get_all_user_tasks(self):
        all_tasks = self.bpmn_workflow.get_tasks(SpiffTask.ANY_MASK)
        return [t for t in all_tasks if not self.bpmn_workflow._is_engine_task(t.task_spec)]

    def get_all_completed_tasks(self):
        all_tasks = self.bpmn_workflow.get_tasks(SpiffTask.ANY_MASK)
        return [t for t in all_tasks
                if not self.bpmn_workflow._is_engine_task(t.task_spec) and t.state in [t.COMPLETED, t.CANCELLED]]

    def get_nav_item(self, task):
        for nav_item in self.bpmn_workflow.get_nav_list():
            if nav_item['task_id'] == task.id:
                return nav_item

    def find_spec_and_field(self, spec_name, field_id):
        """Tracks down a form field by name in the workflow spec(s),
           Returns a tuple of the task, and form"""
        workflows = [self.bpmn_workflow]
        for task in self.bpmn_workflow.get_ready_user_tasks():
            if task.workflow not in workflows:
                workflows.append(task.workflow)
        spec_found = False
        for workflow in workflows:
            for spec in workflow.spec.task_specs.values():
                if spec.name == spec_name:
                    spec_found = True
                    if not hasattr(spec, "form"):
                        raise ApiError("invalid_spec",
                                       "The spec name you provided does not contain a form.")

                    for field in spec.form.fields:
                        if field.id == field_id:
                            return spec, field

                    raise ApiError("invalid_field",
                                   f"The task '{spec_name}' has no field named '{field_id}'")

        raise ApiError("invalid_spec",
                   f"Unable to find a task in the workflow called '{spec_name}'")
