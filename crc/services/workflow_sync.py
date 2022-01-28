import json
import os
from json import JSONDecodeError
from typing import List, Optional

import requests

from crc import app, db
from crc.api.common import ApiError
from crc.models.file import FileModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecCategoryModel


class WorkflowSyncService(object):

    LIBRARY_SPECS = "library specs"
    MASTER_SPECIFICATION = "Master Specification"
    REFERENCE_FILES = "Reference Files"

    SPECIAL_FOLDERS = [LIBRARY_SPECS, MASTER_SPECIFICATION, REFERENCE_FILES]

    @staticmethod
    def sync_with_file_system():
        """Assure the database is in sync with the workflow specifications on the file system.
        We are really just looking at """
        directory = app.config['SYNC_FILE_ROOT']

        directory_items = os.scandir(directory)
        for item in directory_items:
            pass
        # Loop through all top level




    #
    # @staticmethod
    # def process_directory(directory):
    #     files = []
    #     directories = []
    #     directory_items = os.scandir(directory)
    #     for item in directory_items:
    #         if item.is_dir():
    #             directories.append(item)
    #         elif item.is_file():
    #             files.append(item)
    #
    #     return files, directories
    #
    # @staticmethod
    # def process_workflow_spec(json_file, directory):
    #     file_path = os.path.join(directory, json_file)
    #
    #     with open(file_path, 'r') as f_open:
    #         data = f_open.read()
    #         data_obj = json.loads(data)
    #         workflow_spec_model = session.query(WorkflowSpecModel). \
    #             filter(WorkflowSpecModel.id == data_obj['id']). \
    #             first()
    #         if not workflow_spec_model:
    #             category_id = None
    #             if data_obj['category'] is not None:
    #                 category_id = session.query(WorkflowSpecCategoryModel.id).filter(
    #                     WorkflowSpecCategoryModel.display_name == data_obj['category']['display_name']).scalar()
    #             workflow_spec_model = WorkflowSpecModel(id=data_obj['id'],
    #                                                     display_name=data_obj['display_name'],
    #                                                     description=data_obj['description'],
    #                                                     is_master_spec=data_obj['is_master_spec'],
    #                                                     category_id=category_id,
    #                                                     display_order=data_obj['display_order'],
    #                                                     standalone=data_obj['standalone'],
    #                                                     library=data_obj['library'])
    #             session.add(workflow_spec_model)
    #             session.commit()
    #
    #         return workflow_spec_model
    #
    # @staticmethod
    # def process_workflow_spec_file(json_file, spec_directory):
    #     file_path = os.path.join(spec_directory, json_file)
    #
    #     with open(file_path, 'r') as json_handle:
    #         data = json_handle.read()
    #         data_obj = json.loads(data)
    #         spec_file_name = '.'.join(json_file.name.split('.')[:-1])
    #         spec_file_path = os.path.join(spec_directory, spec_file_name)
    #
    #         with open(spec_file_path, 'rb') as spec_handle:
    #             # workflow_spec_name = spec_directory.split('/')[-1]
    #             # workflow_spec = session.query(WorkflowSpecModel).filter(
    #             #     WorkflowSpecModel.display_name == workflow_spec_name).first()
    #
    #             workflow_spec_file_model = session.query(FileModel). \
    #                 filter(FileModel.workflow_spec_id == data_obj['workflow_spec_id']). \
    #                 filter(FileModel.name == spec_file_name). \
    #                 first()
    #             if workflow_spec_file_model:
    #                 # update workflow_spec_file_model
    #                 FileService.update_file(workflow_spec_file_model, spec_handle.read(),
    #                                         CONTENT_TYPES[spec_file_name.split('.')[-1]])
    #             else:
    #                 # create new model
    #                 workflow_spec = session.query(WorkflowSpecModel).filter(
    #                     WorkflowSpecModel.id == data_obj['workflow_spec_id']).first()
    #                 workflow_spec_file_model = FileService.add_workflow_spec_file(workflow_spec,
    #                                                                               name=spec_file_name,
    #                                                                               content_type=CONTENT_TYPES[
    #                                                                                   spec_file_name.split('.')[
    #                                                                                       -1]],
    #                                                                               binary_data=spec_handle.read())
    #
    #         print(f'process_workflow_spec_file: data_obj: {data_obj}')
    #     return workflow_spec_file_model
