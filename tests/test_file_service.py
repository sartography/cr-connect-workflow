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
        FileService.add_task_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  workflow_spec_id=workflow.workflow_spec_id,
                                  task_id=task.id,
                                  name="anything.png", content_type="text",
                                  binary_data=b'1234', irb_doc_code=irb_code)
        # Add the file again with different data
        FileService.add_task_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  workflow_spec_id=workflow.workflow_spec_id,
                                  task_id=task.id,
                                  name="anything.png", content_type="text",
                                  binary_data=b'5678', irb_doc_code=irb_code)

        file_models = FileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEquals(1, len(file_models))
        self.assertEquals(2, file_models[0].latest_version)

    def test_add_file_from_form_increments_version_and_replaces_on_subsequent_add_with_same_name(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_form_field_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  task_id=task.id,
                                  form_field_key=irb_code,
                                  name="anything.png", content_type="text",
                                  binary_data=b'1234')
        # Add the file again with different data
        FileService.add_form_field_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  form_field_key=irb_code,
                                  task_id=task.id,
                                  name="anything.png", content_type="text",
                                  binary_data=b'5678')

        file_models = FileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEquals(1, len(file_models))
        self.assertEquals(2, file_models[0].latest_version)

    def test_add_file_from_form_allows_multiple_files_with_different_names(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('file_upload_form')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_form_field_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  task_id=task.id,
                                  form_field_key=irb_code,
                                  name="anything.png", content_type="text",
                                  binary_data=b'1234')
        # Add the file again with different data
        FileService.add_form_field_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  form_field_key=irb_code,
                                  task_id=task.id,
                                  name="a_different_thing.png", content_type="text",
                                  binary_data=b'5678')
        file_models = FileService.get_workflow_files(workflow_id=workflow.id)
        self.assertEquals(2, len(file_models))
        self.assertEquals(1, file_models[0].latest_version)
        self.assertEquals(1, file_models[1].latest_version)