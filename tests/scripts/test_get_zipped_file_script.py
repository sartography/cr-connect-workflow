from tests.base_test import BaseTest

from crc import session
from crc.models.file import FileModel, FileDataModel
from crc.models.workflow import WorkflowModel
from crc.models.study import StudyModel
from crc.scripts.get_zipped_files import GetZippedFiles
from crc.services.file_service import FileService

import io
import os
import zipfile


class TestGetZippedFiles(BaseTest):

    def test_get_zipped_files(self):
        self.load_example_data()
        study = session.query(StudyModel).order_by(StudyModel.id.desc()).first()
        workflow = session.query(WorkflowModel).first()
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        # Add files to use in the test
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="document_1.png", content_type="text",
                                      task_spec_name=task.name,
                                      binary_data=b'1234', irb_doc_code='Study_Protocol_Document')
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="document_2.txt", content_type="text",
                                      task_spec_name=task.name,
                                      binary_data=b'1234', irb_doc_code='Study_App_Doc')
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="document_3.pdf", content_type="text",
                                      task_spec_name=task.name,
                                      binary_data=b'1234', irb_doc_code='Admin_AdvChklst')

        # Gather the file_ids
        file_ids = []
        files = session.query(FileModel).filter(FileModel.irb_doc_code != '').all()
        for file in files:
            file_ids.append(file.id)

        # Send files to the zipper, receive file_model in return
        file_model = GetZippedFiles().do_task(task, study.id, workflow.id, file_ids=file_ids, filename='another_attachment.zip')
        file_data = session.query(FileDataModel).filter(FileDataModel.file_model_id == file_model.id).first()

        # Test what we get back in the file_model
        with zipfile.ZipFile(io.BytesIO(file_data.data), 'r') as zf:
            self.assertIsInstance(zf, zipfile.ZipFile)
            for name in zf.namelist():
                info = zf.getinfo(name)
                self.assertIn(os.path.basename(info.filename), ['1 Protocol document_1.png', '1 Application document_2.txt', '1  document_3.pdf'])
                file = zf.read(name)
                self.assertEqual(b'1234', file)
