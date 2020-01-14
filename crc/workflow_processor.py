import xml.etree.ElementTree as ElementTree

from SpiffWorkflow.bpmn.BpmnScriptEngine import BpmnScriptEngine
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.camunda.parser.CamundaParser import CamundaParser
from SpiffWorkflow.camunda.serializer.CamundaSerializer import CamundaSerializer

from crc import session
from crc.models.file import FileDataModel, FileModel
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


class WorkflowProcessor:
    _script_engine = CustomBpmnScriptEngine()
    _serializer = CamundaSerializer()

    def __init__(self, workflow_spec_id, bpmn_json):
        self.bpmn_workflow = self._serializer.deserialize_workflow(bpmn_json, wf_spec=self.get_spec(workflow_spec_id))
        self.bpmn_workflow.script_engine = self._script_engine

    @staticmethod
    def get_spec(workflow_spec_id):
        file_data_models = session.query(FileDataModel) \
            .join(FileModel) \
            .filter(FileModel.workflow_spec_id == workflow_spec_id).all()
        parser = CamundaParser()
        for file_data in file_data_models:
            bpmn = ElementTree.fromstring(file_data.data)
            process_id = WorkflowProcessor.__get_process_id(bpmn)
            parser.add_bpmn_xml(bpmn, filename=file_data.file_model.name)
        return parser.get_spec(process_id)

    @classmethod
    def create(cls, workflow_spec_id):
        parser = CamundaParser()
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
    def __get_process_id(et_root):
        process_elements = []
        for child in et_root:
            if child.tag.endswith('process') and child.attrib.get('isExecutable', False):
                process_elements.append(child)

        if len(process_elements) == 0:
            raise Exception('No executable process tag found')

        if len(process_elements) > 1:
            raise Exception('Multiple executable processes tags found')

        return process_elements[0].attrib['id']
