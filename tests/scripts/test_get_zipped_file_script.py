from tests.base_test import BaseTest

from crc import session
from crc.models.file import FileModel, FileDataModel
from crc.services.user_file_service import UserFileService

import io
import os
import zipfile


class TestGetZippedFiles(BaseTest):

    def test_get_zipped_files(self):
        self.create_reference_document()

        workflow = self.create_workflow('get_zip_file')
        study_id = workflow.study_id
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        # Add files to use in the test
        model_1 = UserFileService.add_workflow_file(workflow_id=workflow.id,
                                      name="document_1.png", content_type="text",
                                      task_spec_name=task.name,
                                      binary_data=b'1234', irb_doc_code='Study_Protocol_Document')
        model_2 = UserFileService.add_workflow_file(workflow_id=workflow.id,
                                      name="document_2.txt", content_type="text",
                                      task_spec_name=task.name,
                                      binary_data=b'1234', irb_doc_code='Study_App_Doc')
        model_3 = UserFileService.add_workflow_file(workflow_id=workflow.id,
                                      name="document_3.pdf", content_type="text",
                                      task_spec_name=task.name,
                                      binary_data=b'1234', irb_doc_code='AD_Consent_Model')

        file_ids = [{'file_id': model_1.id}, {'file_id': model_2.id}, {'file_id': model_3.id}]
        workflow_api = self.complete_form(workflow, task, {'file_ids': file_ids})
        next_task = workflow_api.next_task
        file_model_id = next_task.data['zip_file']['id']

        file_data = session.query(FileDataModel).filter(FileDataModel.file_model_id == file_model_id).first()

        # Test what we get back in the zipped file
        with zipfile.ZipFile(io.BytesIO(file_data.data), 'r') as zf:
            self.assertIsInstance(zf, zipfile.ZipFile)
            for name in zf.namelist():
                info = zf.getinfo(name)
                self.assertIn(os.path.basename(info.filename), [f'{study_id} Protocol document_1.png', f'{study_id} Application document_2.txt', f'{study_id} Model document_3.pdf'])
                file = zf.read(name)
                self.assertEqual(b'1234', file)

        # The workflow calls the get_zipped_files script a second time,
        # but we set an IRB Doc Code the second time.
        # So, we expect one to be set in the DB
        self.complete_form(workflow, next_task, {})

        file_1 = session.query(FileModel).filter(FileModel.task_spec == 'Activity_GetZip').first()
        file_2 = session.query(FileModel).filter(FileModel.task_spec == 'Activity_GetZip_2').first()
        # file 1 should *not* have an irb doc code
        self.assertEqual(None, file_1.irb_doc_code)
        # file 2 *should* have an irb doc code
        self.assertEqual('CRC2_IRBSubmission_ZipFile', file_2.irb_doc_code)
