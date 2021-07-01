import re

from SpiffWorkflow.serializer.exceptions import MissingSpecError
from SpiffWorkflow.util.metrics import timeit, firsttime, sincetime
from lxml import etree
import shlex
from datetime import datetime
from typing import List

from SpiffWorkflow import Task as SpiffTask, WorkflowException
from SpiffWorkflow.bpmn.BpmnScriptEngine import BpmnScriptEngine
from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from SpiffWorkflow.bpmn.serializer.BpmnSerializer import BpmnSerializer
from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.camunda.parser.CamundaParser import CamundaParser
from SpiffWorkflow.dmn.parser.BpmnDmnParser import BpmnDmnParser
from SpiffWorkflow.exceptions import WorkflowTaskExecException
from SpiffWorkflow.specs import WorkflowSpec

import crc
from crc import session, app
from crc.api.common import ApiError
from crc.models.file import FileDataModel, FileModel, FileType
from crc.models.task_event import TaskEventModel
from crc.models.user import UserModelSchema
from crc.models.workflow import WorkflowStatus, WorkflowModel, WorkflowSpecDependencyFile
from crc.scripts.script import Script
from crc.services.file_service import FileService
from crc import app
from crc.services.user_service import UserService

from difflib import SequenceMatcher

class CustomBpmnScriptEngine(BpmnScriptEngine):
    """This is a custom script processor that can be easily injected into Spiff Workflow.
    It will execute python code read in from the bpmn.  It will also make any scripts in the
     scripts directory available for execution. """

    def evaluate(self, task, expression):
        """
        Evaluate the given expression, within the context of the given task and
        return the result.
        """
        return self.evaluate_expression(task, expression)

    @timeit
    def execute(self, task: SpiffTask, script, data):

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

            super().execute(task, script, data, externalMethods=augmentMethods)
        except SyntaxError as e:
            raise ApiError('syntax_error',
                           f'Something is wrong with your python script '
                           f'please correct the following:'
                           f' {script}, {e.msg}')
        except NameError as e:
            def get_most_similar(task_data, name_error):
                bad_variable = str(name_error)[6:-16]
                highest_ratio = 0
                most_similar = None
                for item in task_data:
                    ratio = SequenceMatcher(None, item, bad_variable).ratio()
                    if ratio > highest_ratio:
                        most_similar = item
                        highest_ratio = ratio
                return most_similar, int(highest_ratio*100)
            most_similar, highest_ratio = get_most_similar(data, e)
            error_message = f'something you are referencing does not exist: {script}, {e}.'
            if highest_ratio > 50:
                error_message += f' Did you mean \'{most_similar}\'?'
            raise ApiError('name_error', error_message)


    def evaluate_expression(self, task, expression):
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
            exp, valid = self.validateExpression(expression)
            return self._eval(exp, externalMethods=augmentMethods, **task.data)

        except Exception as e:
            raise WorkflowTaskExecException(task,
                                            "Error evaluating expression "
                                            "'%s', %s" % (expression, str(e)))

    def eval(self, exp, data):
        return super()._eval(exp, {}, **data)





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

        if workflow_model.bpmn_workflow_json is None:  # The workflow was never started.
            self.spec_data_files = FileService.get_spec_data_files(
                workflow_spec_id=workflow_model.workflow_spec_id)
            spec = self.get_spec(self.spec_data_files, workflow_model.workflow_spec_id)
        else:
            self.spec_data_files = FileService.get_spec_data_files(
                workflow_spec_id=workflow_model.workflow_spec_id,
                workflow_id=workflow_model.id)
            spec = None

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
                    session.commit()
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
                                   " '%s' version %s, due to a mis-placed or missing task '%s'" %
                                   (self.workflow_spec_id, self.get_version_string(), str(ke)))

        # set whether this is the latest spec file.
        if self.spec_data_files == FileService.get_spec_data_files(workflow_spec_id=workflow_model.workflow_spec_id):
            self.is_latest_spec = True
        else:
            self.is_latest_spec = False

    @staticmethod
    def reset(workflow_model, clear_data=False, delete_files=False):
        print('WorkflowProcessor: reset: ')

        # Try to execute a cancel notify
        try:
            wp = WorkflowProcessor(workflow_model)
            wp.cancel_notify() # The executes a notification to all endpoints that
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
                FileService.delete_file(file.id)
        session.commit()
        return WorkflowProcessor(workflow_model)

    def __get_bpmn_workflow(self, workflow_model: WorkflowModel, spec: WorkflowSpec, validate_only=False):
        if workflow_model.bpmn_workflow_json:
            bpmn_workflow = self._serializer.deserialize_workflow(workflow_model.bpmn_workflow_json,
                                                                  workflow_spec=spec)
        else:
            bpmn_workflow = BpmnWorkflow(spec, script_engine=self._script_engine)
            bpmn_workflow.data[WorkflowProcessor.STUDY_ID_KEY] = workflow_model.study_id
            bpmn_workflow.data[WorkflowProcessor.VALIDATION_PROCESS_KEY] = validate_only
#            try:
#                bpmn_workflow.do_engine_steps()
#            except WorkflowException as we:
#                raise ApiError.from_task_spec("error_loading_workflow", str(we), we.sender)
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
        self.update_dependencies(self.spec_data_files)
        session.add(self.workflow_model)
        session.commit()

    def get_version_string(self):
        # this could potentially become expensive to load all the data in the data models.
        # in which case we might consider using a deferred loader for the actual data, but
        # trying not to pre-optimize.
        file_data_models = FileService.get_spec_data_files(self.workflow_model.workflow_spec_id,
                                                           self.workflow_model.id)
        return WorkflowProcessor.__get_version_string_for_data_models(file_data_models)

    @staticmethod
    def get_latest_version_string_for_spec(spec_id):
        file_data_models = FileService.get_spec_data_files(spec_id)
        return WorkflowProcessor.__get_version_string_for_data_models(file_data_models)

    @staticmethod
    def __get_version_string_for_data_models(file_data_models):
        """Version is in the format v[VERSION] (FILE_ID_LIST)
         For example, a single bpmn file with only one version would be
         v1 (12)  Where 12 is the id of the file data model that is used to create the
         specification.  If multiple files exist, they are added on in
         dot notation to both the version number and the file list. So
         a Spec that includes a BPMN, DMN, an a Word file all on the first
         version would be v1.1.1 (12.45.21)"""

        major_version = 0  # The version of the primary file.
        minor_version = []  # The versions of the minor files if any.
        file_ids = []
        for file_data in file_data_models:
            file_ids.append(file_data.id)
            if file_data.file_model.primary:
                major_version = file_data.version
            else:
                minor_version.append(file_data.version)
        minor_version.insert(0, major_version)  # Add major version to beginning.
        version = ".".join(str(x) for x in minor_version)
        files = ".".join(str(x) for x in file_ids)
        full_version = "v%s (%s)" % (version, files)
        return full_version

    def update_dependencies(self, spec_data_files):
        existing_dependencies = FileService.get_spec_data_files(
            workflow_spec_id=self.workflow_model.workflow_spec_id,
            workflow_id=self.workflow_model.id)

        # Don't save the dependencies if they haven't changed.
        if existing_dependencies == spec_data_files:
            return

        # Remove all existing dependencies, and replace them.
        self.workflow_model.dependencies = []
        for file_data in spec_data_files:
            self.workflow_model.dependencies.append(WorkflowSpecDependencyFile(file_data_id=file_data.id))

    @staticmethod
    @timeit
    def run_master_spec(spec_model, study):
        """Executes a BPMN specification for the given study, without recording any information to the database
        Useful for running the master specification, which should not persist. """
        lasttime = firsttime()
        spec_data_files = FileService.get_spec_data_files(spec_model.id)
        lasttime = sincetime('load Files', lasttime)
        spec = WorkflowProcessor.get_spec(spec_data_files, spec_model.id)
        lasttime = sincetime('get spec', lasttime)
        try:
            bpmn_workflow = BpmnWorkflow(spec, script_engine=WorkflowProcessor._script_engine)
            bpmn_workflow.data[WorkflowProcessor.STUDY_ID_KEY] = study.id
            bpmn_workflow.data[WorkflowProcessor.VALIDATION_PROCESS_KEY] = False
            lasttime = sincetime('get_workflow', lasttime)
            bpmn_workflow.do_engine_steps()
            lasttime = sincetime('run steps', lasttime)
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
    def get_spec(file_data_models: List[FileDataModel], workflow_spec_id):
        """Returns a SpiffWorkflow specification for the given workflow spec,
        using the files provided.  The Workflow_spec_id is only used to generate
        better error messages."""
        parser = WorkflowProcessor.get_parser()
        process_id = None

        for file_data in file_data_models:
            if file_data.file_model.type == FileType.bpmn:
                bpmn: etree.Element = etree.fromstring(file_data.data)
                if file_data.file_model.primary:
                    process_id = FileService.get_process_id(bpmn)
                parser.add_bpmn_xml(bpmn, filename=file_data.file_model.name)
            elif file_data.file_model.type == FileType.dmn:
                dmn: etree.Element = etree.fromstring(file_data.data)
                parser.add_dmn_xml(dmn, filename=file_data.file_model.name)
        if process_id is None:
            raise (ApiError(code="no_primary_bpmn_error",
                            message="There is no primary BPMN model defined for workflow %s" % workflow_spec_id))
        try:
            spec = parser.get_spec(process_id)
        except ValidationException as ve:
            raise ApiError(code="workflow_validation_error",
                           message="Failed to parse Workflow Specification '%s'. \n" % workflow_spec_id +
                                   "Error is %s. \n" % str(ve),
                           file_name=ve.filename,
                           task_id=ve.id,
                           tag=ve.tag)
        return spec

    @staticmethod
    def status_of(bpmn_workflow):
        if bpmn_workflow.is_completed():
            return WorkflowStatus.complete
        user_tasks = bpmn_workflow.get_ready_user_tasks()
        if len(user_tasks) > 0:
            return WorkflowStatus.user_input_required
        else:
            return WorkflowStatus.waiting

    # def hard_reset(self):
    #     """Recreate this workflow. This will be useful when a workflow specification changes.
    #      """
    #     self.spec_data_files = FileService.get_spec_data_files(workflow_spec_id=self.workflow_spec_id)
    #     new_spec = WorkflowProcessor.get_spec(self.spec_data_files, self.workflow_spec_id)
    #     new_bpmn_workflow = BpmnWorkflow(new_spec, script_engine=self._script_engine)
    #     new_bpmn_workflow.data = self.bpmn_workflow.data
    #     try:
    #         new_bpmn_workflow.do_engine_steps()
    #     except WorkflowException as we:
    #         raise ApiError.from_task_spec("hard_reset_engine_steps_error", str(we), we.sender)
    #     self.bpmn_workflow = new_bpmn_workflow

    def get_status(self):
        return self.status_of(self.bpmn_workflow)

    def do_engine_steps(self):
        try:
            self.bpmn_workflow.refresh_waiting_tasks()
            self.bpmn_workflow.do_engine_steps()
        except WorkflowTaskExecException as we:
            raise ApiError.from_task("task_error", str(we), we.task)

    def cancel_notify(self):
        try:
            self.bpmn_workflow.cancel_notify()
        except WorkflowTaskExecException as we:
            raise ApiError.from_task("task_error", str(we), we.task)

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
        if self.bpmn_workflow.is_completed():
            for task in SpiffTask.Iterator(self.bpmn_workflow.task_tree, SpiffTask.ANY_MASK):
                if isinstance(task.task_spec, EndEvent):
                    return task

        # If there are ready tasks to complete, return the next ready task, but return the one
        # in the active parallel path if possible.  In some cases the active parallel path may itself be
        # a parallel gateway with multiple tasks, so prefer ones that share a parent.
        ready_tasks = self.bpmn_workflow.get_tasks(SpiffTask.READY)
        if len(ready_tasks) > 0:
            for task in ready_tasks:
                if task.parent == self.bpmn_workflow.last_task:
                    return task
            for task in ready_tasks:
                if self.bpmn_workflow.last_task and task.parent == self.bpmn_workflow.last_task.parent:
                    return task

            return ready_tasks[0]

        # If there are no ready tasks, but the thing isn't complete yet, find the first non-complete task
        # and return that
        next_task = None
        for task in SpiffTask.Iterator(self.bpmn_workflow.task_tree, SpiffTask.NOT_FINISHED_MASK):
            next_task = task
        return next_task

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
        """Tracks down a form field by name in the workflow spec,
         only looks at ready tasks. Returns a tuple of the task, and form"""
        for spec in self.bpmn_workflow.spec.task_specs.values():
            if spec.name == spec_name and hasattr(spec, "form"):
                for field in spec.form.fields:
                    if field.id == field_id:
                        return spec, field
        raise ApiError("invalid_field",
                       "Unable to find a task in the workflow with a lookup field called: %s" % field_id)
