from tests.base_test import BaseTest

from crc.services.file_service import FileService
from crc.scripts.request_approval import RequestApproval
from crc.services.workflow_processor import WorkflowProcessor
from crc.api.common import ApiError

from crc import db
from crc.models.approval import ApprovalModel


class TestRequestApprovalScript(BaseTest):

    def test_do_task(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        task.data = {"study": {"approval1": "dhf8r", 'approval2':'lb3dp'}}
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code="UVACompl_PRCAppr",
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234')
        script = RequestApproval()
        script.do_task(task, workflow.study_id, workflow.id, "study.approval1", "study.approval2")
        self.assertEqual(2, db.session.query(ApprovalModel).count())

    def test_do_task_with_blank_second_approver(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        task.data = {"study": {"approval1": "dhf8r", 'approval2':''}}
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      irb_doc_code="UVACompl_PRCAppr",
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234')
        script = RequestApproval()
        script.do_task(task, workflow.study_id, workflow.id, "study.approval1", "study.approval2")
        self.assertEqual(1, db.session.query(ApprovalModel).count())


    def test_do_task_with_incorrect_argument(self):
        """This script should raise an error if it can't figure out the approvers."""
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        task.data = {"approvals": {'dhf8r':["invalid"], 'lb3dp':"invalid"}}
        script = RequestApproval()
        with self.assertRaises(ApiError):
            script.do_task(task, workflow.study_id, workflow.id, "approvals")

    def test_do_task_validate_only(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('empty_workflow')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        task.data = {"study": {"approval1": "dhf8r", 'approval2':'lb3dp'}}

        script = RequestApproval()
        script.do_task_validate_only(task, workflow.study_id, workflow.id, "study.approval1")
        self.assertEqual(0, db.session.query(ApprovalModel).count())

