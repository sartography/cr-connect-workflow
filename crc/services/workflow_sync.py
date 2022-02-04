import json
import os
from json import JSONDecodeError
from typing import List, Optional

import marshmallow
import requests

from crc import app, db, ma
from crc.api.common import ApiError
from crc.models.file import FileModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecCategoryModel, WorkflowSpecCategoryModelSchema, \
    WorkflowSpecModelSchema, WorkflowLibraryModel
from crc.services.file_system_service import FileSystemService
from crc.services.spec_file_service import SpecFileService


class WorkflowSyncService(object):
    """
    There are some files on the File System that should be used to determine what Categories and Workflow
    Specifications are available.  The FileSyncService and WorkflowSyncService both look to the filesytem for
    everything, but we still track our workflow spec metadata and categories in the database.  This will
    allow us to write that information to disk, and update our database from disk as needed.
    """

    LIBRARY_SPECS = "Library Specs"
    MASTER_SPECIFICATION = "Master Specification"
    REFERENCE_FILES = "Reference Files"
    SPECIAL_FOLDERS = [LIBRARY_SPECS, MASTER_SPECIFICATION, REFERENCE_FILES]
    JSON_FILE = "categories.json"

    def from_file_system(self):
        """Assure the database is in sync with the workflow specifications on the file system. """
        if not os.path.exists(FileSystemService.root_path()):
            raise ApiError('missing_specs', 'The path for workflow specifications does not exist.')
        json_path = os.path.join(FileSystemService.root_path(), self.JSON_FILE)
        if not os.path.exists(json_path):
            raise ApiError('missing_category_file', 'The path for workflow specifications must contain a json'
                                                    ' file that describes the categories.')

        directory_items = os.scandir(FileSystemService.root_path())
        # Load the categories.
        with open(json_path) as json_file:
            data = json.load(json_file)
        existing_cats = db.session.query(WorkflowSpecCategoryModel).all()
        # SqlAlchemy will attempt to update existing models if it can find them.
        categories = WorkflowSpecCategoryModelSchema(many=True).load(data['categories'], session=db.session)
        db.session.add_all(categories)

        # For each category, load up the workflow files
        # also Load the master workflow, and library workflows
        for cat in categories:
            path = SpecFileService.category_path(cat.display_name)
            if os.path.exists(path):
                self.__load_workflows(cat.display_name, cat)
            else:
                # Fixme:  What if there are running workflows?  Do those relationships cause this to fail?
                db.session.query(WorkflowSpecModel).filter(WorkflowSpecModel.category_id == cat.id).delete()
                db.session.delete(cat)
        self.__load_workflows(self.LIBRARY_SPECS)
        self.__load_workflows(self.MASTER_SPECIFICATION)
        db.session.commit()

    @staticmethod
    def __load_workflows(directory, category=None):
        """Creates workflow models for all directories in the given directory"""
        path = SpecFileService.category_path(directory)
        for wd in os.listdir(path):
            wf_json_path = os.path.join(path, wd, 'workflow.json')
            if not os.path.exists(wf_json_path):
                raise ApiError('missing_workflow_meta_file',
                               'Each directory containing a workflow must contain a '
                               'workflow.json file.')
            with open(wf_json_path) as wf_json_file:
                data = json.load(wf_json_file)
            workflow = WorkflowSpecModelSchema().load(data, session=db.session)
            if category:
                workflow.category = category
            db.session.add(workflow)
            # Connect Libraries
            for lib in data['libraries']:
                lib = WorkflowLibraryModel(workflow_spec_id=workflow.id,
                                           library_spec_id=lib['id'])
                db.session.add(lib)

    def to_file_system(self):
        """Writes metadata about the specifications to json files, and assures
        directory structures are correct. """
        categories = db.session.query(WorkflowSpecCategoryModel).all()
        data = ExportData(categories, None, None)
        my_data = ExportDataSchema().dump(data)
        json_file = os.path.join(FileSystemService.root_path(), self.JSON_FILE)
        os.makedirs(os.path.dirname(json_file), exist_ok=True)
        with open(json_file, 'w') as f:
            json.dump(my_data, f, indent=4)

        for wf in db.session.query(WorkflowSpecModel).all():
            self.workflow_to_file_system(wf)

    def workflow_to_file_system(self, wf: WorkflowSpecModel):
        path = SpecFileService.workflow_path(wf)
        json_data = WorkflowSpecModelSchema().dump(wf)
        file = os.path.join(path, 'workflow.json')
        with open(file, 'w') as f:
            json.dump(json_data, f, indent=4)


class ExportData(object):
    def __init__(self, categories: List[WorkflowSpecCategoryModel],
                 master_spec: WorkflowSpecModel,
                 libraries: List[WorkflowSpecModel]):
        self.categories = categories
        self.master_spec = master_spec
        self.libraries = libraries


class ExportDataSchema(ma.Schema):
    class Meta:
        model = ExportData
        fields = ["categories"]
    categories = marshmallow.fields.List(marshmallow.fields.Nested(WorkflowSpecCategoryModelSchema))


