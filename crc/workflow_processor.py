import xml.etree.ElementTree as ElementTree

from SpiffWorkflow.bpmn.BpmnScriptEngine import BpmnScriptEngine
from SpiffWorkflow.bpmn.parser.task_parsers import UserTaskParser
from SpiffWorkflow.bpmn.parser.util import full_tag
from SpiffWorkflow.bpmn.serializer.BpmnSerializer import BpmnSerializer
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.camunda.parser.CamundaParser import CamundaParser
from SpiffWorkflow.dmn.parser.BpmnDmnParser import BpmnDmnParser

from crc import session
from crc.models.file import FileDataModel, FileModel, FileType
from crc.models.workflow import WorkflowStatus


class CustomBpmnScriptEngine(BpmnScriptEngine):
    """This is a custom script processor that can be easily injected into Spiff Workflow.
    Rather than execute arbitrary code, this assumes the script references a fully qualified python class
    such as myapp.RandomFact. """

    def execute(self, task, script, **kwargs):
        """
        Assume that the script read in from the BPMN file is a fully qualified python class. Instantiate
        that class, pass in any data available to the current task so that it might act on it.
        Assume that the class implements the "do_task" method.

        This allows us to reference custom code from the BPMN diagram.
        """
        module_name = "crc." + script
        class_name = module_name.split(".")[-1]
        mod = __import__(module_name, fromlist=[class_name])
        klass = getattr(mod, class_name)
        klass().do_task(task.data)


class MyCustomParser(BpmnDmnParser):
    """
    A BPMN and DMN parser that can also parse Camunda forms.
    """
    OVERRIDE_PARSER_CLASSES = BpmnDmnParser.OVERRIDE_PARSER_CLASSES
    OVERRIDE_PARSER_CLASSES.update(CamundaParser.OVERRIDE_PARSER_CLASSES)


class WorkflowProcessor:
    _script_engine = CustomBpmnScriptEngine()
    _serializer = BpmnSerializer()

    def __init__(self, workflow_spec_id, bpmn_json):
        wf_spec = self.get_spec(workflow_spec_id)
        self.bpmn_workflow = self._serializer.deserialize_workflow(bpmn_json, workflow_spec=wf_spec)
        self.bpmn_workflow.script_engine = self._script_engine

    @staticmethod
    def get_parser():
        parser = MyCustomParser()
        return parser

    @staticmethod
    def get_spec(workflow_spec_id):
        parser = WorkflowProcessor.get_parser()
        process_id = None
        file_data_models = session.query(FileDataModel) \
            .join(FileModel) \
            .filter(FileModel.workflow_spec_id == workflow_spec_id).all()
        for file_data in file_data_models:
            if file_data.file_model.type == FileType.bpmn:
                bpmn: ElementTree.Element = ElementTree.fromstring(file_data.data)
                if file_data.file_model.primary:
                    process_id = WorkflowProcessor.__get_process_id(bpmn)
                parser.add_bpmn_xml(bpmn, filename=file_data.file_model.name)
            elif file_data.file_model.type == FileType.dmn:
                dmn: ElementTree.Element = ElementTree.fromstring(file_data.data)
                parser.add_dmn_xml(dmn, filename=file_data.file_model.name)
        if process_id is None:
            raise(Exception("There is no primary BPMN model defined for workflow " + workflow_spec_id))
        return parser.get_spec(process_id)

    @classmethod
    def create(cls, workflow_spec_id):
        spec = WorkflowProcessor.get_spec(workflow_spec_id)
        bpmn_workflow = BpmnWorkflow(spec, script_engine=cls._script_engine)
        bpmn_workflow.do_engine_steps()
        json = cls._serializer.serialize_workflow(bpmn_workflow)
        processor = cls(workflow_spec_id, json)
        return processor

    def get_status(self):
        if self.bpmn_workflow.is_completed():
            return WorkflowStatus.complete
        user_tasks = self.bpmn_workflow.get_ready_user_tasks()
        if len(user_tasks) > 0:
            return WorkflowStatus.user_input_required
        else:
            return WorkflowStatus.waiting

    def do_engine_steps(self):
        self.bpmn_workflow.do_engine_steps()

    def serialize(self):
        return self._serializer.serialize_workflow(self.bpmn_workflow)

    def next_user_tasks(self):
        return self.bpmn_workflow.get_ready_user_tasks()

    def complete_task(self, task):
        self.bpmn_workflow.complete_task_from_id(task.id)

    def get_data(self):
        return self.bpmn_workflow.data

    def get_ready_user_tasks(self):
        return self.bpmn_workflow.get_ready_user_tasks()

    @staticmethod
    def __get_process_id(et_root: ElementTree.Element):
        process_elements = []
        for child in et_root:
            if child.tag.endswith('process') and child.attrib.get('isExecutable', False):
                process_elements.append(child)

        if len(process_elements) == 0:
            raise Exception('No executable process tag found')

        if len(process_elements) > 1:
            raise Exception('Multiple executable processes tags found')

        return process_elements[0].attrib['id']
