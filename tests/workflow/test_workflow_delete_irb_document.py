from tests.base_test import BaseTest
from crc.services.file_service import FileService
from crc.scripts.is_file_uploaded import IsFileUploaded
import io


class TestDeleteIRBDocument(BaseTest):

    def test_delete_irb_document(self):
        self.load_example_data()
        irb_code = 'Study_Protocol_Document'

        workflow = self.create_workflow('add_delete_irb_document')
        study_id = workflow.study_id

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        files = FileService.get_files_for_study(study_id)
        self.assertEqual(0, len(files))
        self.assertEqual(False, IsFileUploaded.do_task(IsFileUploaded, first_task, study_id, workflow.id, irb_code))

        # Add a file
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="filename.txt", content_type="text",
                                      binary_data=b'1234', irb_doc_code=irb_code)
        self.assertEqual(True, IsFileUploaded.do_task(IsFileUploaded, first_task, study_id, workflow.id, irb_code))

        self.complete_form(workflow, first_task, {'irb_document': irb_code})
        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.assertEqual('# Is file uploaded\nuploaded:  True', second_task.documentation)

        self.complete_form(workflow, second_task, {})
        workflow_api = self.get_workflow_api(workflow)
        third_task = workflow_api.next_task
        self.assertEqual('# Is file deleted\ndeleted:  True', third_task.documentation)

        print('test_delete_irb_document')