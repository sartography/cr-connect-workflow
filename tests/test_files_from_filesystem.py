from tests.base_test import BaseTest

from crc import app, session
from crc.models.file import FileModel, FileDataModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowSpecCategoryModel, WorkflowSpecCategoryModelSchema
from crc.services.workflow_service import WorkflowService
import os
import json

from crc.services.file_service import FileService


def process_directory(directory):
    files = []
    directories = []
    directory_items = os.scandir(directory)
    for item in directory_items:
        if item.is_dir():
            directories.append(item)
        elif item.is_file():
            files.append(item)

    return files, directories


def process_workflow_spec(json_file, directory):
    file_path = os.path.join(directory, json_file)

    with open(file_path, 'r') as f_open:
        data = f_open.read()
        data_obj = json.loads(data)
        workflow_spec_model = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.display_name==data_obj['display_name']).first()
        if not workflow_spec_model:
            category_id = session.query(WorkflowSpecCategoryModel.id).filter(WorkflowSpecCategoryModel.display_name==data_obj['display_name']).scalar()
            workflow_spec_model = WorkflowSpecModel(id=data_obj['id'],
                                                    display_name=data_obj['display_name'],
                                                    description=data_obj['description'],
                                                    is_master_spec=data_obj['is_master_spec'],
                                                    category_id=category_id,
                                                    display_order=data_obj['display_order'],
                                                    standalone=data_obj['standalone'],
                                                    library=data_obj['library'])
            session.add(workflow_spec_model)

    session.commit()

    print(f'process_workflow_spec: workflow_spec_model: {workflow_spec_model}')
    return workflow_spec_model


def process_workflow_spec_files():
    pass


def process_category(json_file, root):
    print(f'process_category: json_file: {json_file}')
    file_path = os.path.join(root, json_file)

    with open(file_path, 'r') as f_open:
        data = f_open.read()
        data_obj = json.loads(data)
        category = session.query(WorkflowSpecCategoryModel).filter(
            WorkflowSpecCategoryModel.display_name == data_obj['display_name']).first()
        if not category:
            category = WorkflowSpecCategoryModel(display_name=data_obj['display_name'],
                                                      display_order=data_obj['display_order'],
                                                      admin=data_obj['admin'])
            session.add(category)
        else:
            category.display_order = data_obj['display_order']
            category.admin = data_obj['admin']
        # print(data)
        print(f'process_category: category: {category}')

    session.commit()
    return category


def process_workflow_spec_directory(spec_directory):
    print(f'process_workflow_spec_directory: {spec_directory}')
    files, directories = process_directory(spec_directory)

    for file in files:
        print(f'process_workflow_spec_directory: file: {file}')


def process_category_directory(category_directory):
    print(f'process_category_directory: {category_directory}')
    files, directories = process_directory(category_directory)

    for file in files:
        if file.name.endswith('.json'):
            workflow_spec = process_workflow_spec(file, category_directory)

    for workflow_spec_directory in directories:
        directory_path = os.path.join(category_directory, workflow_spec_directory)
        process_workflow_spec_directory(directory_path)


def process_root_directory(root_directory):

    files, directories = process_directory(root_directory)
    for file in files:
        if file.name.endswith('.json'):
            category_model = process_category(file, root_directory)
    WorkflowService.cleanup_workflow_spec_category_display_order()

    for directory in directories:
        directory_path = os.path.join(root_directory, directory)
        process_category_directory(directory_path)


def update_file_metadata_from_filesystem(root_directory):
    process_root_directory(root_directory)


class TestFilesFromFilesystem(BaseTest):

    def test_files_from_filesystem(self):

        self.load_example_data()
        SYNC_FILE_ROOT = os.path.join(app.root_path, '..', 'files')
        update_file_metadata_from_filesystem(SYNC_FILE_ROOT)

        print(f'test_files_from_filesystem')
