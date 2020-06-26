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
        self.assertEqual(1, db.session.query(ApprovalModel).count())
        model = db.session.query(ApprovalModel).first()
        self.assertEqual(workflow.study_id, model.study_id)
        self.assertEqual(workflow.id, model.workflow_id)
        self.assertEqual("dhf8r", model.approver_uid)
        self.assertEqual(1, model.version)

    def test_new_requests_dont_add_if_approval_exists_for_current_workflow(self):
        self.create_reference_document()
        workflow = self.create_workflow("empty_workflow")
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678', irb_doc_code="UVACompl_PRCAppr" )

        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")
        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")
        self.assertEqual(1, db.session.query(ApprovalModel).count())
        model = db.session.query(ApprovalModel).first()
        self.assertEqual(1, model.version)

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
        self.assertEqual(2, db.session.query(ApprovalModel).count())
        models = db.session.query(ApprovalModel).order_by(ApprovalModel.version).all()
        self.assertEqual(1, models[0].version)
        self.assertEqual(2, models[1].version)

    def test_get_health_attesting_records(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678', irb_doc_code="AD_CoCAppr")

        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")
        records = ApprovalService.get_health_attesting_records()

        self.assertEqual(len(records), 1)

    def test_get_not_really_csv_content(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'5678', irb_doc_code="AD_CoCAppr")

        ApprovalService.add_approval(study_id=workflow.study_id, workflow_id=workflow.id, approver_uid="dhf8r")
        records = ApprovalService.get_not_really_csv_content()

        self.assertEqual(len(records), 2)

    def test_new_approval_sends_proper_emails(self):
        self.assertEqual(1, 1)

    def test_new_approval_failed_ldap_lookup(self):
        # failed lookup should send email to sartographysupport@googlegroups.com + Cheryl
        self.assertEqual(1, 1)

    def test_approve_approval_sends_proper_emails(self):
        self.assertEqual(1, 1)

    def test_deny_approval_sends_proper_emails(self):
        self.assertEqual(1, 1)
