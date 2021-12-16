from tests.base_test import BaseTest

from crc import app, session
from crc.models.file import FileModel, FileDataModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecCategoryModel
from crc.services.file_service import FileService

import os


class TestFilesToFilesystem(BaseTest):

    def test_files_to_filesystem(self):

        # # category = filename = ''
        # # data = 'asdf'
        # self.load_example_data()
        #
        # file_model = session.query(FileModel).first()
        # # filename = file_model.name
        # file_data_model = session.query(FileDataModel).filter(FileDataModel.file_model_id == file_model.id).first()
        # if file_model.workflow_spec_id is None:
        #     file_model.workflow_spec_id = 'random_fact'
        # workflow_spec_model = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id == file_model.workflow_spec_id).first()
        # if workflow_spec_model.category_id is None:
        #     workflow_spec_model.category_id = 0
        # category_model = session.query(WorkflowSpecCategoryModel).filter(WorkflowSpecCategoryModel.id == workflow_spec_model.category_id).first()
        # file_path = os.path.join(app.root_path, '..', 'files', category_model.display_name, file_model.name)
        # os.makedirs(os.path.dirname(file_path), exist_ok=True)
        #
        # with open(file_path, 'wb') as f_handle:
        #     f_handle.write(file_data_model.data)

        print('test_files_to_filesystem')
