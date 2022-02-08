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
        display_order = self.next_display_order(spec)
        spec.display_order = display_order
        self.update_spec(spec)

    def update_spec(self, spec:WorkflowSpecInfo, rescan=True):
        spec_path = self.workflow_path(spec)
        if(spec.is_master_spec or spec.library or spec.standalone):
            spec.category_id = ""
        os.makedirs(spec_path, exist_ok=True)
        json_path = os.path.join(spec_path, self.WF_JSON_FILE)
        with open(json_path, "w") as wf_json:
            json.dump(self.WF_SCHEMA.dump(spec), wf_json, indent=4)
        if rescan:
            self.scan_file_system()

    def delete_spec(self, spec_id: str):
        if spec_id in self.specs:
            spec = self.specs[spec_id]
            path = self.workflow_path(spec)
            shutil.rmtree(path)
            self.scan_file_system()

    def get_spec(self, spec_id: str):
        if spec_id not in self.specs:
            return None
        return self.specs[spec_id]

    def get_specs(self):
        return list(self.specs.values())

    def reorder_spec(self, spec:WorkflowSpecInfo, direction):
        workflows = spec.category.workflows
        workflows.sort(key=lambda w: w.display_order)
        index = workflows.index_of(spec)
        if direction == 'up' and index > 0:
            workflows[index-1], workflows[index] = workflows[index], workflows[index-1]
        if direction == 'down' and index < len(workflows):
            workflows[index+1], workflows[index] = workflows[index], workflows[index+1]
        return self.cleanup_workflow_spec_display_order(spec.category.id)

    def cleanup_workflow_spec_display_order(self, category_id):
        index = 0
        category = self.get_category(category_id)
        if not category:
            return []
        for workflow in category.workflows:
            workflow.display_order = index
            self.update_spec(workflow)
            index += 1
        return category.workflows

    def get_libraries(self) -> List[WorkflowSpecInfo]:
        spec_list = self.libraries.workflows
        spec_list.sort(key=lambda w: w.display_order)
        return spec_list

    def get_standalones(self) -> List[WorkflowSpecInfo]:
        spec_list = list(self.standalone.workflows)
        spec_list.sort(key=lambda w: w.display_order)
        return spec_list

    def get_categories(self) -> List[WorkflowSpecCategory]:
        """Returns the categories as a list in display order"""
        cat_list = list(self.categories.values())
        cat_list.sort(key=lambda w: w.display_order)
        return cat_list

    def get_category(self, category_id) -> WorkflowSpecCategory:
        if category_id not in self.categories:
            return None
        return self.categories[category_id]

    def add_category(self, category: WorkflowSpecCategory):
        return self.update_category(category)

    def update_category(self, category: WorkflowSpecCategory, rescan=True):
        cat_path = self.category_path(category.display_name)
        os.makedirs(cat_path, exist_ok=True)
        json_path = os.path.join(cat_path, self.CAT_JSON_FILE)
        with open(json_path, "w") as cat_json:
            json.dump(self.CAT_SCHEMA.dump(category), cat_json, indent=4)
        if rescan:
            self.scan_file_system()
        return self.categories[category.id]

    def delete_category(self, category_id: str):
        if category_id in self.categories:
            path = self.category_path(category_id)
            shutil.rmtree(path)
            self.scan_file_system()
        self.cleanup_category_display_order()
        self.scan_file_system()

    def reorder_workflow_spec_category(self, cat: WorkflowSpecCategory, direction):
        cats = self.get_categories() # Returns an ordered list
        index = cats.index_of(cat)
        if direction == 'up' and index > 0:
            cats[index-1], cats[index] = cats[index], cats[index-1]
        if direction == 'down' and index < len(cats):
            cats[index+1], cats[index] = cats[index], cats[index+1]
        index = 0
        for category in cats:
            category.display_order = index
            self.update_category(category, rescan=False)
            index += 1
        return cats

    def cleanup_category_display_order(self):
        cats = self.get_categories() # Returns an ordered list
        index = 0
        for category in cats:
            category.display_order = index
            self.update_category(category, rescan=False)
            index += 1
        return cats

    def scan_file_system(self):
        """Build a model of our workflows, based on the file system structure and json files"""

        # Clear out existing values
        self.categories = {}
        self.specs = {}
        self.master_spec = None
        self.libraries = {}
        self.standalone = {}

        if not os.path.exists(FileSystemService.root_path()):
            return # Nothing to scan yet.  There are no files.

        directory_items = os.scandir(FileSystemService.root_path())
        for item in directory_items:
            if item.is_dir():
                if item.name == self.LIBRARY_SPECS:
                    self.scan_category(item, is_library=True)
                elif item.name == self.STAND_ALONE_SPECS:
                    self.scan_category(item, is_standalone=True)
                elif item.name == self.MASTER_SPECIFICATION:
                    self.scan_spec(item, is_master=True)
                else:
                    self.scan_category(item)

    def scan_category(self, dir_item: os.DirEntry, is_library=False, is_standalone=False):
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
        elif is_standalone:
            self.standalone = cat
        else:
            self.categories[cat.id] = cat
        workflow_dirs = os.scandir(dir_item.path)
        for item in workflow_dirs:
            if item.is_dir():
                self.scan_spec(item, category=cat)
        cat.workflows.sort(key=lambda w: w.display_order)
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
                                    primary_file_name="", display_order=0, is_review=False,
                                    libraries=[])
            with open(spec_path, "w") as wf_json:
                json.dump(self.WF_SCHEMA.dump(spec), wf_json, indent=4)
        if is_master:
            self.master_spec = spec
        elif category:
            spec.category = category
            category.workflows.append(spec)
        self.specs[spec.id] = spec


