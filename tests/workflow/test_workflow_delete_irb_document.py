from tests.base_test import BaseTest
from crc.api.common import ApiError
from crc.scripts.is_file_uploaded import IsFileUploaded
from crc.services.user_file_service import UserFileService


class TestDeleteIRBDocument(BaseTest):

    def test_delete_irb_document(self):
        self.create_reference_document()
        irb_code = 'Study_Protocol_Document'

        workflow = self.create_workflow('add_delete_irb_document')
        study_id = workflow.study_id

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        # Should not have any files yet
        files = UserFileService.get_files_for_study(study_id)
        self.assertEqual(0, len(files))
        self.assertEqual(False, IsFileUploaded.do_task(
            IsFileUploaded, first_task, study_id, workflow.id, irb_code))

        # Add a file
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name=first_task.name,
                                          name="filename.txt", content_type="text",
                                          binary_data=b'1234', irb_doc_code=irb_code)
        # Assert we have the file
        self.assertEqual(True, IsFileUploaded.do_task(
            IsFileUploaded, first_task, study_id, workflow.id, irb_code))

        # run the workflow, which deletes the file
        self.complete_form(workflow, first_task, {'irb_document': irb_code})
        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        # make sure it is deleted
        self.assertEqual(False, IsFileUploaded.do_task(
            IsFileUploaded, second_task, study_id, workflow.id, irb_code))

    def test_delete_irb_document_list(self):
        # try deleting a list of files
        self.create_reference_document()
        irb_code_1 = 'Study_Protocol_Document'
        irb_code_2 = 'Study_App_Doc'
        irb_codes = [irb_code_1, irb_code_2]

        workflow = self.create_workflow('add_delete_irb_document')
        study_id = workflow.study_id

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        # Should not have any files yet
        files = UserFileService.get_files_for_study(study_id)
        self.assertEqual(0, len(files))
        self.assertEqual(False, IsFileUploaded.do_task(IsFileUploaded, first_task, study_id, workflow.id, irb_code_1))
        self.assertEqual(False, IsFileUploaded.do_task(IsFileUploaded, first_task, study_id, workflow.id, irb_code_2))

        # Add a file
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name=first_task.name,
                                          name="filename.txt", content_type="text",
                                          binary_data=b'1234', irb_doc_code=irb_code_1)
        # Add another file
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name=first_task.name,
                                          name="filename.txt", content_type="text",
                                          binary_data=b'1234', irb_doc_code=irb_code_2)
        self.assertEqual(True, IsFileUploaded.do_task(
            IsFileUploaded, first_task, study_id, workflow.id, irb_code_1))
        self.assertEqual(True, IsFileUploaded.do_task(
            IsFileUploaded, first_task, study_id, workflow.id, irb_code_2))

        self.complete_form(workflow, first_task, {'irb_document': irb_codes})
        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.assertEqual(False, IsFileUploaded.do_task(
            IsFileUploaded, second_task, study_id, workflow.id, irb_code_1))
        self.assertEqual(False, IsFileUploaded.do_task(
            IsFileUploaded, second_task, study_id, workflow.id, irb_code_2))

    def test_delete_irb_document_no_document(self):


        irb_code = 'Study_Protocol_Document'
        workflow = self.create_workflow('add_delete_irb_document')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        # There is no document to delete, so we get an error
        with self.assertRaises(AssertionError) as ex:
            self.complete_form(workflow, first_task, {'irb_document': irb_code})

    def test_delete_irb_document_bad_document(self):

        # This is a bad document code
        irb_code = 'Study_Protocol_Doc'
        workflow = self.create_workflow('add_delete_irb_document')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        # bad document code, so we should get an error
        with self.assertRaises(AssertionError):
            self.complete_form(workflow, first_task, {'irb_document': irb_code})
