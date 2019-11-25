from io import BytesIO
from xml.etree import ElementTree

from SpiffWorkflow.bpmn.serializer.BpmnSerializer import BpmnSerializer
from SpiffWorkflow.bpmn.serializer.Packager import Packager
from SpiffWorkflow.bpmn.specs import ExclusiveGateway

from app.camunda.CamundaParser import CamundaExclusiveGatewayParser


class InMemoryPackager(Packager):
    """
    Creates spiff's wf packages on the fly.
    """

    @classmethod
    def package_in_memory(cls, workflow_name, workflow_files, editor):
        """
        Generates wf packages from workflow diagrams.
        """

        s = BytesIO()
        p = cls(s, workflow_name, meta_data=[], editor=editor)
        p.add_bpmn_files_by_glob(workflow_files)
        p.create_package()
        return s.getvalue()


class WorkflowRunner:
    def __init__(self, path, workflow_process_id=None, debug=False, **kwargs):
        self.path = path
        self.debug = debug
        self.kwargs = kwargs

        root_element = ElementTree.parse(self.path).getroot() # definitions

        self.workflowProcessID = workflow_process_id or self.__get_workflow_process_id(root_element)
        self.workflowEditor = root_element.attrib['exporter']

        self.packager = InMemoryPackager
        #if self.workflowEditor == 'Camunda Modeler':
        #    self.addParserSupport('exclusiveGateway', CamundaExclusiveGatewayParser, ExclusiveGateway.ExclusiveGateway)

        self.workflow = None

    def get_spec(self):
        package = self.packager.package_in_memory(self.workflowProcessID, self.path, self.workflowEditor)
        return BpmnSerializer().deserialize_workflow_spec(package)

    @staticmethod
    def __get_workflow_process_id(root_element):
        process_elements = []
        for child in root_element:
            if child.tag.endswith('process') and child.attrib.get('isExecutable', False):
                process_elements.append(child)

        if len(process_elements) == 0:
            raise Exception('No executable process tag found')

        if len(process_elements) > 1:
            raise Exception('Multiple executable processes tags found')

        return process_elements[0].attrib['id']
