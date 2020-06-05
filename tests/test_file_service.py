from tests.base_test import BaseTest
from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor


class TestFileService(BaseTest):
    """Largely tested via the test_file_api, and time is tight, but adding new tests here."""

    def test_add_file_from_task_increments_version_and_replaces_on_subsequent_add(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234', irb_doc_code=irb_code)
        # Add the file again with different data
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678', irb_doc_code=irb_code)

        file_models = FileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEqual(1, len(file_models))

        file_data = FileService.get_workflow_data_files(workflow_id=workflow.id)
        self.assertEqual(1, len(file_data))
        self.assertEqual(2, file_data[0].version)


    def test_add_file_from_form_increments_version_and_replaces_on_subsequent_add_with_same_name(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234')
        # Add the file again with different data
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678')

        file_models = FileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEqual(1, len(file_models))

        file_data = FileService.get_workflow_data_files(workflow_id=workflow.id)
        self.assertEqual(1, len(file_data))
        self.assertEqual(2, file_data[0].version)

    def test_add_file_from_form_allows_multiple_files_with_different_names(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234')
        # Add the file again with different data
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code=irb_code,
                                      name="a_different_thing.png", content_type="text",
                                      binary_data=b'5678')
        file_models = FileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEqual(2, len(file_models))
