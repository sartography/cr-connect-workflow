from tests.base_test import BaseTest
from crc import db
from crc.models.approval import ApprovalModel
from crc.services.approval_service import ApprovalService
from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor


class TestApprovalsService(BaseTest):

    def test_create_approval_record(self):
        self.create_reference_document()
        workflow = self.create_workflow("empty_workflow")
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678', irb_doc_code="UVACompl_PRCAppr" )

        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")
        self.assertEquals(1, db.session.query(ApprovalModel).count())
        model = db.session.query(ApprovalModel).first()
        self.assertEquals(workflow.study_id, model.study_id)
        self.assertEquals(workflow.id, model.workflow_id)
        self.assertEquals("dhf8r", model.approver_uid)
        self.assertEquals(1, model.version)

    def test_new_requests_dont_add_if_approval_exists_for_current_workflow(self):
        self.create_reference_document()
        workflow = self.create_workflow("empty_workflow")
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678', irb_doc_code="UVACompl_PRCAppr" )

        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")
        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")
        self.assertEquals(1, db.session.query(ApprovalModel).count())
        model = db.session.query(ApprovalModel).first()
        self.assertEquals(1, model.version)

    def test_new_approval_requests_after_file_modification_create_new_requests(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678', irb_doc_code="AD_CoCAppr")

        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")

        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678', irb_doc_code="UVACompl_PRCAppr")

        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")
        self.assertEquals(2, db.session.query(ApprovalModel).count())
        models = db.session.query(ApprovalModel).order_by(ApprovalModel.version).all()
        self.assertEquals(1, models[0].version)
        self.assertEquals(2, models[1].version)


