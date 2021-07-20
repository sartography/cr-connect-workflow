from tests.base_test import BaseTest
from crc.services.file_service import FileService
from crc.scripts.is_file_uploaded import IsFileUploaded


class TestIsFileUploaded(BaseTest):

    def test_file_uploaded_pass(self):
        self.load_example_data()
        irb_code_1 = 'UVACompl_PRCAppr'
        irb_code_2 = 'Study_App_Doc'

        workflow = self.create_workflow('empty_workflow')
        first_task = self.get_workflow_api(workflow).next_task
        study_id = workflow.study_id

        # We shouldn't have any files yet.
        files = FileService.get_files_for_study(study_id)
        self.assertEqual(0, len(files))
        self.assertEqual(False, IsFileUploaded.do_task(IsFileUploaded, first_task, study_id, workflow.id, irb_code_1))

        # Add a file
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="something.png", content_type="text",
                                      binary_data=b'1234', irb_doc_code=irb_code_1)

        # Make sure we find the file
        files = FileService.get_files_for_study(study_id)
        self.assertEqual(1, len(files))
        self.assertEqual(True, IsFileUploaded.do_task(IsFileUploaded, first_task, study_id, workflow.id, irb_code_1))

        # Add second file
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678', irb_doc_code=irb_code_2)

        # Make sure we find both files.
        files = FileService.get_files_for_study(study_id)
        self.assertEqual(2, len(files))
        self.assertEqual(True, IsFileUploaded.do_task(IsFileUploaded, first_task, study_id, workflow.id, irb_code_1))
        self.assertEqual(True, IsFileUploaded.do_task(IsFileUploaded, first_task, study_id, workflow.id, irb_code_2))
