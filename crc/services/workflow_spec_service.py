import json
import os
import shutil
from typing import List

from crc.api.common import ApiError
from crc.models.workflow import WorkflowSpecCategory, WorkflowSpecCategorySchema, WorkflowSpecInfo, \
    WorkflowSpecInfoSchema
from crc.services.file_system_service import FileSystemService


class WorkflowSpecService(FileSystemService):

    """This is a way of persisting json files to the file system in a way that mimics the data
    as it would have been stored in the database. This is specific to Workflow Specifications, and
     Workflow Specification categories.
     We do this, so we can easily drop in a new configuration on the file system, and change all
      the workflow specs at once, or manage those file in a git repository. """

    CAT_SCHEMA = WorkflowSpecCategorySchema()
    WF_SCHEMA = WorkflowSpecInfoSchema()

    def add_spec(self, spec: WorkflowSpecInfo):
        display_order = self.next_display_order(spec)
        spec.display_order = display_order
        self.update_spec(spec)

    def update_spec(self, spec:WorkflowSpecInfo):
        spec_path = self.workflow_path(spec)
        if spec.is_master_spec or spec.library or spec.standalone:
            spec.category_id = ""
        os.makedirs(spec_path, exist_ok=True)
        json_path = os.path.join(spec_path, self.WF_JSON_FILE)
        with open(json_path, "w") as wf_json:
            json.dump(self.WF_SCHEMA.dump(spec), wf_json, indent=4)

    def delete_spec(self, spec_id: str):
        spec = self.get_spec(spec_id)
        if not spec:
            return
        if spec.library:
            self.__remove_library_references(spec.id)
        path = self.workflow_path(spec)
        shutil.rmtree(path)

    def __remove_library_references(self, spec_id):
        for spec in self.get_specs():
            if spec_id in spec.libraries:
                spec.libraries.remove(spec_id)
                self.update_spec(spec)

    @property
    def master_spec(self):
        return self.get_master_spec()

    def get_master_spec(self):
        path = os.path.join(FileSystemService.root_path(), FileSystemService.MASTER_SPECIFICATION)
        return self.__scan_spec(path, FileSystemService.MASTER_SPECIFICATION)

    def get_spec(self, spec_id):
        if not os.path.exists(FileSystemService.root_path()):
            return # Nothing to scan yet.  There are no files.
        if spec_id == 'master_spec':
            return self.get_master_spec()
        with os.scandir(FileSystemService.root_path()) as category_dirs:
            for item in category_dirs:
                category_dir = item
                if item.is_dir():
                    with os.scandir(item.path) as spec_dirs:
                        for sd in spec_dirs:
                            if sd.name == spec_id:
                                # Now we have the category direcotry, and spec directory
                                category = self.__scan_category(category_dir)
                                return self.__scan_spec(sd.path, sd.name, category)

    def get_specs(self):
        categories = self.get_categories()
        specs = []
        for cat in categories:
            specs.extend(cat.specs)
        return specs

    def reorder_spec(self, spec:WorkflowSpecInfo, direction):
        specs = spec.category.specs
        specs.sort(key=lambda w: w.display_order)
        index = specs.index(spec)
        if direction == 'up' and index > 0:
            specs[index-1], specs[index] = specs[index], specs[index-1]
        if direction == 'down' and index < len(specs)-1:
            specs[index+1], specs[index] = specs[index], specs[index+1]
        return self.cleanup_workflow_spec_display_order(spec.category)

    def cleanup_workflow_spec_display_order(self, category):
        index = 0
        if not category:
            return []
        for workflow in category.specs:
            workflow.display_order = index
            self.update_spec(workflow)
            index += 1
        return category.specs

    def get_categories(self) -> List[WorkflowSpecCategory]:
        """Returns the categories as a list in display order"""
        cat_list = self.__scan_categories()
        cat_list.sort(key=lambda w: w.display_order)
        return cat_list

    def get_libraries(self) -> List[WorkflowSpecInfo]:
        cat = self.get_category(self.LIBRARY_SPECS)
        if not cat:
            return []
        return cat.specs

    def get_standalones(self) -> List[WorkflowSpecInfo]:
        cat = self.get_category(self.STAND_ALONE_SPECS)
        if not cat:
            return []
        return cat.specs

    def get_category(self, category_id):
        """Look for a given category, and return it."""
        if not os.path.exists(FileSystemService.root_path()):
            return  # Nothing to scan yet.  There are no files.
        with os.scandir(FileSystemService.root_path()) as directory_items:
            for item in directory_items:
                if item.is_dir() and item.name == category_id:
                    return self.__scan_category(item)

    def add_category(self, category: WorkflowSpecCategory):
        display_order = len(self.get_categories())
        category.display_order = display_order
        return self.update_category(category)

    def update_category(self, category: WorkflowSpecCategory):
        cat_path = self.category_path(category.id)
        os.makedirs(cat_path, exist_ok=True)
        json_path = os.path.join(cat_path, self.CAT_JSON_FILE)
        with open(json_path, "w") as cat_json:
            json.dump(self.CAT_SCHEMA.dump(category), cat_json, indent=4)
        return category

    def delete_category(self, category_id: str):
        path = self.category_path(category_id)
        if os.path.exists(path):
            shutil.rmtree(path)
        self.cleanup_category_display_order()

    def reorder_workflow_spec_category(self, cat: WorkflowSpecCategory, direction):
        cats = self.get_categories()  # Returns an ordered list
        index = cats.index(cat)
        if direction == 'up' and index > 0:
            cats[index-1], cats[index] = cats[index], cats[index-1]
        if direction == 'down' and index < len(cats)-1:
            cats[index+1], cats[index] = cats[index], cats[index+1]
        index = 0
        for category in cats:
            category.display_order = index
            self.update_category(category)
            index += 1
        return cats

    def cleanup_category_display_order(self):
        cats = self.get_categories()  # Returns an ordered list
        index = 0
        for category in cats:
            category.display_order = index
            self.update_category(category)
            index += 1
        return cats

    def __scan_categories(self):
        if not os.path.exists(FileSystemService.root_path()):
            return [] # Nothing to scan yet.  There are no files.

        with os.scandir(FileSystemService.root_path()) as directory_items:
            categories = []
            for item in directory_items:
                if item.is_dir():
                    if item.name == self.REFERENCE_FILES:
                        continue
                    elif item.name == self.MASTER_SPECIFICATION:
                        continue
                    elif item.name == self.LIBRARY_SPECS:
                        continue
                    elif item.name == self.STAND_ALONE_SPECS:
                        continue
                    categories.append(self.__scan_category(item))
            return categories

    def __scan_category(self, dir_item: os.DirEntry):
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
        with os.scandir(dir_item.path) as workflow_dirs:
            cat.specs = []
            for item in workflow_dirs:
                if item.is_dir():
                    cat.specs.append(self.__scan_spec(item.path, item.name, category=cat))
            cat.specs.sort(key=lambda w: w.display_order)
        return cat

    @staticmethod
    def _get_workflow_metas(study_id):
        # Add in the Workflows for each category
        # Fixme: moved fro the Study Service
        workflow_metas = []
#        for workflow in workflow_models:
#            workflow_metas.append(WorkflowMetadata.from_workflow(workflow))
        return workflow_metas

    def __scan_spec(self, path, name, category=None):
        spec_path = os.path.join(path, self.WF_JSON_FILE)
        is_master = FileSystemService.MASTER_SPECIFICATION in spec_path

        if os.path.exists(spec_path):
            with open(spec_path) as wf_json:
                data = json.load(wf_json)
                spec = self.WF_SCHEMA.load(data)
        else:
            spec = WorkflowSpecInfo(id=name, library=False, standalone=False, is_master_spec=is_master,
                                    display_name=name, description="", primary_process_id="",
                                    primary_file_name="", display_order=0, is_review=False,
                                    libraries=[])
            with open(spec_path, "w") as wf_json:
                json.dump(self.WF_SCHEMA.dump(spec), wf_json, indent=4)
        if category:
            spec.category = category
            spec.category_id = category.id
        return spec
