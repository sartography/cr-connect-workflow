import json
import os
import shutil
from typing import List

from SpiffWorkflow.bpmn.parser.ValidationException import ValidationException
from lxml import etree

from crc.api.common import ApiError
from crc.models.file import FileType
from crc.models.workflow import WorkflowSpecCategory, WorkflowSpecCategorySchema, WorkflowSpecInfo, \
    WorkflowSpecInfoSchema
from crc.services.file_system_service import FileSystemService


class WorkflowSpecService(FileSystemService):

    CAT_JSON_FILE = "category.json"
    WF_JSON_FILE = "workflow.json"
    CAT_SCHEMA = WorkflowSpecCategorySchema()
    WF_SCHEMA = WorkflowSpecInfoSchema()

    """We store details about the specifications and categories on the file system.
        This service handles changes and persistence of workflow specs and category specs.
    """
    def __init__(self):
        self.categories = {}
        self.specs = {}
        self.master_spec = None
        self.libraries = {}
        self.standalone = {}
        self.scan_file_system()

    def add_spec(self, spec: WorkflowSpecInfo):
        self.update_spec(spec)

    def update_spec(self, spec:WorkflowSpecInfo):
        spec_path = self.workflow_path(spec)
        os.makedirs(os.path.dirname(spec_path), exist_ok=True)
        json_path = os.path.join(spec_path, self.WF_JSON_FILE)
        with open(json_path, "w") as wf_json:
            json.dump(self.WF_SCHEMA.dump(spec), wf_json, indent=4)
        self.scan_file_system()

    def delete_spec(self, spec_id: str):
        if spec_id in self.specs:
            spec = self.specs[spec_id]
            path = self.workflow_path(spec)
            shutil.rmtree(path)
            self.scan_file_system()

    def get_spec(self, spec_id: str):
        if spec_id not in self.specs:
            raise ApiError('unknown spec', 'unable to find a spec with id:' + spec_id)
        return self.specs[spec_id]

    def reorder_spec(self, spec:WorkflowSpecInfo, direction):
        workflows = spec.category.workflows
        workflows.sort(key=lambda w: w.display_order)
        index = workflows.index_of(spec)
        if direction == 'up' and index > 0:
            workflows[index-1], workflows[index] = workflows[index], workflows[index-1]
        if direction == 'down' and index < len(workflows):
            workflows[index+1], workflows[index] = workflows[index], workflows[index+1]
        index = 0
        for workflow in workflows:
            workflow.display_order = index
            self.save_spec(workflow)
            index += 1
        return workflows

    def get_libraries(self) -> List[WorkflowSpecInfo]:
        # fixme
        pass

    def get_categories(self) -> List[WorkflowSpecCategory]:
        pass

    def get_category(self, category_id) -> WorkflowSpecCategory:
        pass

    def add_category(self, category: WorkflowSpecCategory):
        pass

    def update_category(self, category: WorkflowSpecCategory):
        pass

    def delete_category(self, category: WorkflowSpecCategory):
        pass

    def reorder_workflow_spec_category(self, spec:WorkflowSpecInfo, direction):
        # Fixme:  Resort Workflow categories
        pass

    def scan_file_system(self):
        """Build a model of our workflows, based on the file system structure and json files"""

        # Clear out existing values
        self.categories = {}
        self.specs = {}
        self.master_spec = None
        self.libraries = {}
        if not os.path.exists(FileSystemService.root_path()):
            raise ApiError('missing_specs', 'The path for workflow specifications does not exist.')
        directory_items = os.scandir(FileSystemService.root_path())
        for item in directory_items:
            if item.is_dir():
                if item.name == self.LIBRARY_SPECS:
                    self.scan_category(item, is_library=True)
                elif item.name == self.MASTER_SPECIFICATION:
                    self.scan_spec(item, is_master=True)
                else:
                    self.scan_category(item)

    def scan_category(self, dir_item: os.DirEntry, is_library=False):
        """Reads the category.json file, and any workflow directories """
        cat_path = os.path.join(dir_item.path, self.CAT_JSON_FILE)
        if os.path.exists(cat_path):
            with open(cat_path) as cat_json:
                data = json.load(cat_json)
                cat = self.CAT_SCHEMA.load(data)
        else:
            cat = WorkflowSpecCategory(id=dir_item.name, display_name=dir_item.name, display_order=10000, admin=False)
            with open(cat_path, "w") as wf_json:
                json.dump(self.CAT_SCHEMA.dump(cat), wf_json, indent=4)
        if is_library:
            self.libraries = cat
        else:
            self.categories[cat.id] = cat
        workflow_dirs = os.scandir(FileSystemService.root_path())
        for item in workflow_dirs:
            self.scan_spec(item, category=cat)
        return cat

    @staticmethod
    def _get_workflow_metas(study_id):
        # Add in the Workflows for each category
        # Fixme: moved fro the Study Service
        workflow_metas = []
#        for workflow in workflow_models:
#            workflow_metas.append(WorkflowMetadata.from_workflow(workflow))
        return workflow_metas


    def scan_spec(self, dir_item: os.DirEntry, is_master=False, category=None):
        if not is_master and not category:
            raise ApiError("invalid_spec_dir", "Please specify what category this workflow belongs to.")
        spec_path = os.path.join(dir_item.path, self.WF_JSON_FILE)
        if os.path.exists(spec_path):
            with open(spec_path) as wf_json:
                data = json.load(wf_json)
                spec = self.WF_SCHEMA.load(data)
        else:
            spec = WorkflowSpecInfo(id=dir_item.name, library=False, standalone=False, is_master_spec=is_master,
                                    display_name=dir_item.name, description="", primary_process_id="",
                                    primary_file_name="")
            with open(spec_path, "w") as wf_json:
                json.dump(WorkflowSpecInfoSchema.dump(spec), wf_json, indent=4)
        if is_master:
            self.master_spec = spec
        elif category:
            self.specs[spec.id] = spec
            spec.category = category
            category.workflow_specs.append(spec)

    def set_primary_bpmn(self, workflow_spec: WorkflowSpecInfo, file_name: str, binary_data=None):
        # If this is a BPMN, extract the process id, and determine if it is contains swim lanes.
        extension = self.get_extension(file_name)
        file_type = FileType[extension]
        if file_type == FileType.bpmn:
            if not binary_data:
                binary_data = self.get_data(workflow_spec, file_name)
            try:
                bpmn: etree.Element = etree.fromstring(binary_data)
                workflow_spec.primary_process_id = self.get_process_id(bpmn)
                workflow_spec.primary_file_name = file_name
                workflow_spec.is_review = self.has_swimlane(bpmn)

            except etree.XMLSyntaxError as xse:
                raise ApiError("invalid_xml", "Failed to parse xml: " + str(xse), file_name=file_name)
        else:
            raise ApiError("invalid_xml", "Only a BPMN can be the primary file.", file_name=file_name)

    @staticmethod
    def has_swimlane(et_root: etree.Element):
        """
        Look through XML and determine if there are any lanes present that have a label.
        """
        elements = et_root.xpath('//bpmn:lane',
                                 namespaces={'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'})
        retval = False
        for el in elements:
            if el.get('name'):
                retval = True
        return retval

    @staticmethod
    def get_process_id(et_root: etree.Element):
        process_elements = []
        for child in et_root:
            if child.tag.endswith('process') and child.attrib.get('isExecutable', False):
                process_elements.append(child)

        if len(process_elements) == 0:
            raise ValidationException('No executable process tag found')

        # There are multiple root elements
        if len(process_elements) > 1:

            # Look for the element that has the startEvent in it
            for e in process_elements:
                this_element: etree.Element = e
                for child_element in list(this_element):
                    if child_element.tag.endswith('startEvent'):
                        return this_element.attrib['id']

            raise ValidationException('No start event found in %s' % et_root.attrib['id'])

        return process_elements[0].attrib['id']

