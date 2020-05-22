from tests.base_test import BaseTest


class TestApprovals(BaseTest):

    def test_list_approvals(self):
        rv = self.app.get('/v1.0/approval', headers=self.logged_in_headers())
        self.assert_success(rv)

    def test_update_approval(self):
        rv = self.app.put('/v1.0/approval/1',
                          headers=self.logged_in_headers(),
                          data={})
        self.assert_success(rv)
