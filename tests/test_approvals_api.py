from tests.base_test import BaseTest


class TestApprovals(BaseTest):
    def setUp(self):
        """Initial setup shared by all TestApprovals tests"""
        self.load_example_data()
        self.workflow = self.create_workflow('random_fact')

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
        rv = self.app.put('/v1.0/approval/1',
                          headers=self.logged_in_headers(),
                          data={})
        self.assert_success(rv)
