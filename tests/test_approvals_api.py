import json
from tests.base_test import BaseTest

from crc import app, db, session
from crc.models.approval import ApprovalModel


class TestApprovals(BaseTest):
    def setUp(self):
        """Initial setup shared by all TestApprovals tests"""
        self.load_example_data()
        self.study = self.create_study()
        self.workflow = self.create_workflow('random_fact')
        # TODO: Move to base_test as a helper
        self.approval = ApprovalModel(
            study=self.study,
            workflow=self.workflow,
            approver_uid='bgb22',
            status='WAITING', # TODO: Use enumerate options
            version=1
        )
        session.add(self.approval)
        session.commit()

    def test_list_approvals_per_approver(self):
        """Only approvals associated with approver should be returned"""
        rv = self.app.get('/v1.0/approval', headers=self.logged_in_headers())
        self.assert_success(rv)

    def test_list_approvals_per_admin(self):
        """All approvals will be returned"""
        rv = self.app.get('/v1.0/approval', headers=self.logged_in_headers())
        self.assert_success(rv)

    def test_update_approval(self):
        """Approval status will be updated"""
        body = {
            'approver_uid': 'rvr98',
            'status': 'DECLINED'
        }
        approval_id = self.approval.id
        rv = self.app.put(f'/v1.0/approval/{approval_id}',
                          content_type="application/json",
                          headers=self.logged_in_headers(),
                          data=json.dumps(body))
        self.assert_success(rv)
