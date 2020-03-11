import json
import re
import xml.etree.ElementTree as ElementTree

from SpiffWorkflow import Task as SpiffTask, Workflow
from SpiffWorkflow.bpmn.BpmnScriptEngine import BpmnScriptEngine
from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from SpiffWorkflow.bpmn.serializer.BpmnSerializer import BpmnSerializer
from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.camunda.parser.CamundaParser import CamundaParser
from SpiffWorkflow.dmn.parser.BpmnDmnParser import BpmnDmnParser
from SpiffWorkflow.operators import Operator

from crc import session, db
from crc.api.common import ApiError
from crc.models.file import FileDataModel, FileModel, FileType
from crc.models.workflow import WorkflowStatus, WorkflowModel
from crc.scripts.script import Script


class CustomBpmnScriptEngine(BpmnScriptEngine):
    """This is a custom script processor that can be easily injected into Spiff Workflow.
    Rather than execute arbitrary code, this assumes the script references a fully qualified python class
    such as myapp.RandomFact. """

    def execute(self, task:SpiffTask, script, **kwargs):
        """
        Assume that the script read in from the BPMN file is a fully qualified python class. Instantiate
        that class, pass in any data available to the current task so that it might act on it.
        Assume that the class implements the "do_task" method.

        This allows us to reference custom code from the BPMN diagram.
        """
        commands = script.split(" ")
        path_and_command = commands[0].rsplit(".", 1)
        if len(path_and_command) == 1:
            module_name = "crc.scripts." + self.camel_to_snake(path_and_command[0])
            class_name = path_and_command[0]
        else:
            module_name = "crc.scripts." + path_and_command[0] + "." + self.camel_to_snake(path_and_command[1])
            class_name = path_and_command[1]
        try:
            mod = __import__(module_name, fromlist=[class_name])
            klass = getattr(mod, class_name)
            study_id = task.workflow.data[WorkflowProcessor.STUDY_ID_KEY]
            if not isinstance(klass(), Script):
                raise ApiError("invalid_script",
                               "This is an internal error. The script '%s:%s' you called  "
                               "does not properly implement the CRC Script class." %
                               (module_name, class_name))
            klass().do_task(task, study_id, *commands[1:])
        except ModuleNotFoundError as mnfe:
            raise ApiError("invalid_script",
                           "Unable to locate Script: '%s:%s'" % (module_name, class_name), 400)

    @staticmethod
    def camel_to_snake(camel):
        camel = camel.strip()
        return re.sub(r'(?<!^)(?=[A-Z])', '_', camel).lower()

    def evaluate(self, task, expression):
        """
        Evaluate the given expression, within the context of the given task and
        return the result.
        """
        if isinstance(expression, Operator):
            return expression._matches(task)
        else:
            return self._eval(task, expression, **task.data)

    def _eval(self, task, expression, **kwargs):
        locals().update(kwargs)
        try :
            return eval(expression)
        except NameError as ne:
            raise ApiError('invalid_expression',
                           'The expression you provided does not exist:' + expression)


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

    def __init__(self, workflow_model: WorkflowModel, soft_reset=False, hard_reset=False):
        """Create a Workflow Processor based on the serialized information available in the workflow model.
        If soft_reset is set to true, it will try to use the latest version of the workflow specification.
        If hard_reset is set to true, it will create a new Workflow, but embed the data from the last
        completed task in the previous workflow.
        If neither flag is set, it will use the same version of the specification that was used to originally
        create the workflow model. """
        orig_version = workflow_model.spec_version
        if soft_reset:
            spec = self.get_spec(workflow_model.workflow_spec_id)
            workflow_model.spec_version = spec.description
        else:
            spec = self.get_spec(workflow_model.workflow_spec_id, workflow_model.spec_version)

        self.workflow_spec_id = workflow_model.workflow_spec_id
        try:
            self.bpmn_workflow = self._serializer.deserialize_workflow(workflow_model.bpmn_workflow_json, workflow_spec=spec)
        except KeyError as ke:
            if soft_reset:
                # Undo the soft-reset.
                workflow_model.spec_version = orig_version
            orig_version = workflow_model.spec_version
            raise ApiError(code="unexpected_workflow_structure",
                           message="Failed to deserialize workflow '%s' version %s, due to a mis-placed or missing task '%s'" %
                                   (self.workflow_spec_id, workflow_model.spec_version, str(ke)) +
                           " This is very likely due to a soft reset where there was a structural change.")
        self.bpmn_workflow.script_engine = self._script_engine

        if hard_reset:
            # Now that the spec is loaded, get the data and rebuild the bpmn with the new details
            workflow_model.spec_version = self.hard_reset()

    @staticmethod
    def get_parser():
        parser = MyCustomParser()
        return parser

    @staticmethod
    def get_latest_version_string(workflow_spec_id):
        """Version is in the format v[VERSION] (FILE_ID_LIST)
         For example, a single bpmn file with only one version would be
         v1 (12)  Where 12 is the id of the file data model that is used to create the
         specification.  If multiple files exist, they are added on in
         dot notation to both the version number and the file list. So
         a Spec that includes a BPMN, DMN, an a Word file all on the first
         version would be v1.1.1 (12.45.21)"""

        # this could potentially become expensive to load all the data in the data models.
        # in which case we might consider using a deferred loader for the actual data, but
        # trying not to pre-optimize.
        file_data_models = WorkflowProcessor.__get_latest_file_models(workflow_spec_id)
        major_version = 0  # The version of the primary file.
        minor_version = []  # The versions of the minor files if any.
        file_ids = []
        for file_data in file_data_models:
            file_ids.append(file_data.id)
            if file_data.file_model.primary:
                major_version = file_data.version
            else:
                minor_version.append(file_data.version)
        minor_version.insert(0, major_version) # Add major version to beginning.
        version = ".".join(str(x) for x in minor_version)
        files = ".".join(str(x) for x in file_ids)
        full_version = "v%s (%s)" % (version, files)
        return full_version

    @staticmethod
    def __get_file_models_for_version(workflow_spec_id, version):
        file_id_strings = re.findall('\((.*)\)', version)[0].split(".")
        file_ids = [int(i) for i in file_id_strings]
        files = session.query(FileDataModel)\
            .join(FileModel) \
            .filter(FileModel.workflow_spec_id == workflow_spec_id)\
            .filter(FileDataModel.id.in_(file_ids)).all()
        if len(files) != len(file_ids):
            raise ApiError("invalid_version",
                           "The version '%s' of workflow specification '%s' is invalid.  Unable to locate the correct files to recreate it." %
                           (version, workflow_spec_id))
        return files

    @staticmethod
    def __get_latest_file_models(workflow_spec_id):
        """Returns all the latest files related to a workflow specification"""
        return session.query(FileDataModel) \
            .join(FileModel) \
            .filter(FileModel.workflow_spec_id == workflow_spec_id)\
            .filter(FileDataModel.version == FileModel.latest_version)\
            .order_by(FileModel.id)\
            .all()


    @staticmethod
    def get_spec(workflow_spec_id, version=None):
        """Returns the requested version of the specification,
        or the lastest version if none is specified."""
        parser = WorkflowProcessor.get_parser()
        process_id = None
        if version is None:
            file_data_models = WorkflowProcessor.__get_latest_file_models(workflow_spec_id)
            version = WorkflowProcessor.get_latest_version_string(workflow_spec_id)
        else:
            file_data_models = WorkflowProcessor.__get_file_models_for_version(workflow_spec_id, version)
        for file_data in file_data_models:
            if file_data.file_model.type == FileType.bpmn:
                bpmn: ElementTree.Element = ElementTree.fromstring(file_data.data)
                if file_data.file_model.primary:
                    process_id = WorkflowProcessor.get_process_id(bpmn)
                parser.add_bpmn_xml(bpmn, filename=file_data.file_model.name)
            elif file_data.file_model.type == FileType.dmn:
                dmn: ElementTree.Element = ElementTree.fromstring(file_data.data)
                parser.add_dmn_xml(dmn, filename=file_data.file_model.name)
        if process_id is None:
            raise(Exception("There is no primary BPMN model defined for workflow %s" % workflow_spec_id))
        try:
            spec = parser.get_spec(process_id)
        except ValidationException as ve:
            raise ApiError(code="workflow_validation_error",
                           message="Failed to parse Workflow Specification '%s' %s." % (workflow_spec_id, version) +
                                   "Error is %s" % str(ve))
        spec.description = version
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

    @classmethod
    def create(cls,  study_id, workflow_spec_id):
        spec = WorkflowProcessor.get_spec(workflow_spec_id)
        bpmn_workflow = BpmnWorkflow(spec, script_engine=cls._script_engine)
        bpmn_workflow.data[WorkflowProcessor.STUDY_ID_KEY] = study_id
        bpmn_workflow.do_engine_steps()
        workflow_model = WorkflowModel(status=WorkflowProcessor.status_of(bpmn_workflow),
                                       study_id=study_id,
                                       workflow_spec_id=workflow_spec_id,
                                       spec_version=spec.description)
        session.add(workflow_model)
        session.commit()
        # Need to commit twice, first to get a unique id for the workflow model, and
        # a second time to store the serilaization so we can maintain this link within
        # the spiff-workflow process.
        bpmn_workflow.data[WorkflowProcessor.WORKFLOW_ID_KEY] = workflow_model.id

        workflow_model.bpmn_workflow_json = WorkflowProcessor._serializer.serialize_workflow(bpmn_workflow)
        session.add(workflow_model)
        session.commit()
        processor = cls(workflow_model)
        return processor

    def hard_reset(self):
        """Recreate this workflow, but keep the data from the last completed task and add it back into the first task.
         This may be useful when a workflow specification changes, and users need to review all the
         prior steps, but don't need to reenter all the previous data.

         Returns the new version.
         """
        spec = WorkflowProcessor.get_spec(self.workflow_spec_id)
        bpmn_workflow = BpmnWorkflow(spec, script_engine=self._script_engine)
        bpmn_workflow.data = self.bpmn_workflow.data
        for task in bpmn_workflow.get_tasks(SpiffTask.READY):
            task.data = self.bpmn_workflow.last_task.data
        bpmn_workflow.do_engine_steps()
        self.bpmn_workflow = bpmn_workflow
        return spec.description

    def get_status(self):
        return self.status_of(self.bpmn_workflow)

    def get_spec_version(self):
        """We use the spec's descrption field to store the version information"""
        return self.bpmn_workflow.spec.description

    def do_engine_steps(self):
        self.bpmn_workflow.do_engine_steps()

    def serialize(self):
        return self._serializer.serialize_workflow(self.bpmn_workflow)

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
            last_task = None
            for task in SpiffTask.Iterator(self.bpmn_workflow.task_tree, SpiffTask.ANY_MASK):
                if isinstance(task.task_spec, EndEvent):
                    return task

        # If there are ready tasks to complete, return the next ready task, but return the one
        # in the active parallel path if possible.
        ready_tasks = self.bpmn_workflow.get_tasks(SpiffTask.READY)
        if len(ready_tasks) > 0:
            for task in ready_tasks:
                if task.parent == self.bpmn_workflow.last_task:
                    return task
            return ready_tasks[0]

        # If there are no ready tasks, but the thing isn't complete yet, find the first non-complete task
        # and return that
        next_task = None
        for task in SpiffTask.Iterator(self.bpmn_workflow.task_tree, SpiffTask.NOT_FINISHED_MASK):
            next_task = task
        return next_task

    def complete_task(self, task):
        self.bpmn_workflow.complete_task_from_id(task.id)

    def get_data(self):
        return self.bpmn_workflow.data

    def get_workflow_id(self):
        return self.bpmn_workflow.data[self.WORKFLOW_ID_KEY]

    def get_study_id(self):
        return self.bpmn_workflow.data[self.STUDY_ID_KEY]

    def get_ready_user_tasks(self):
        return self.bpmn_workflow.get_ready_user_tasks()

    def get_all_user_tasks(self):
        all_tasks = self.bpmn_workflow.get_tasks(SpiffTask.ANY_MASK)
        return [t for t in all_tasks if not self.bpmn_workflow._is_engine_task(t.task_spec)]

    @staticmethod
    def get_process_id(et_root: ElementTree.Element):
        process_elements = []
        for child in et_root:
            if child.tag.endswith('process') and child.attrib.get('isExecutable', False):
                process_elements.append(child)

        if len(process_elements) == 0:
            raise Exception('No executable process tag found')

        # There are multiple root elements
        if len(process_elements) > 1:

            # Look for the element that has the startEvent in it
            for e in process_elements:
                this_element: ElementTree.Element = e
                for child_element in list(this_element):
                    if child_element.tag.endswith('startEvent'):
                        return this_element.attrib['id']

            raise Exception('No start event found in %s' % et_root.attrib['id'])

        return process_elements[0].attrib['id']
