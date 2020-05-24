from tests.base_test import BaseTest
from crc import db
from crc.models.approval import ApprovalModel
from crc.services.approval_service import ApprovalService
from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor


class TestApprovalsService(BaseTest):

    def test_create_approval_record(self):
        workflow = self.create_workflow("empty_workflow")
        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")
        self.assertEquals(1, db.session.query(ApprovalModel).count())
        model = db.session.query(ApprovalModel).first()
        self.assertEquals(workflow.study_id, model.study_id)
        self.assertEquals(workflow.id, model.workflow_id)
        self.assertEquals("dhf8r", model.approver_uid)
        self.assertEquals(1, model.version)
        self.assertIsNotNone(model.workflow_hash)

    def test_new_requests_dont_add_if_approval_exists_for_current_workflow(self):
        workflow = self.create_workflow("empty_workflow")
        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")
        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")
        self.assertEquals(1, db.session.query(ApprovalModel).count())
        model = db.session.query(ApprovalModel).first()
        self.assertEquals(1, model.version)

    def test_new_approval_requests_after_file_modification_create_new_requests(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()

        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")

        irb_code_1 = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_task_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  workflow_spec_id=workflow.workflow_spec_id,
                                  task_id=task.id,
                                  name="anything.png", content_type="text",
                                  binary_data=b'5678', irb_doc_code=irb_code_1)

        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")
        self.assertEquals(2, db.session.query(ApprovalModel).count())
        models = db.session.query(ApprovalModel).order_by(ApprovalModel.version).all()
        self.assertEquals(1, models[0].version)
        self.assertEquals(2, models[1].version)


    def test_generate_workflow_hash_and_version(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        irb_code_1 = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        irb_code_2 = "NonUVAIRB_AssuranceForm"  # The second file in above.
        # Add a task file to the workflow.
        FileService.add_task_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  workflow_spec_id=workflow.workflow_spec_id,
                                  task_id=task.id,
                                  name="anything.png", content_type="text",
                                  binary_data=b'5678', irb_doc_code=irb_code_1)
        # Add a two form field files with the same irb_code, but
        FileService.add_form_field_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  task_id=task.id,
                                  form_field_key=irb_code_2,
                                  name="anything.png", content_type="text",
                                  binary_data=b'1234')
        FileService.add_form_field_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  form_field_key=irb_code_2,
                                  task_id=task.id,
                                  name="another_anything.png", content_type="text",
                                  binary_data=b'5678')


        # Workflow hash should look be id[1]-id[1]-id[1]
        # Sould be three files, each with a version of 1.
        # where id is the file id, which we don't know, thus the regex.
        latest_files = FileService.get_workflow_files(workflow.id)
        self.assertRegexpMatches(ApprovalService._generate_workflow_hash(latest_files), "\d+\[1\]-\d+\[1\]-\d+\[1\]")

        # Replace last file
        # should now be id[1]-id[1]-id[2]
        FileService.add_form_field_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  form_field_key=irb_code_2,
                                  task_id=task.id,
                                  name="another_anything.png", content_type="text",
                                  binary_data=b'9999')
        self.assertRegexpMatches(ApprovalService._generate_workflow_hash(latest_files), "\d+\[1\]-\d+\[1\]-\d+\[2\]")

