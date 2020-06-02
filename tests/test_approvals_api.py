import json
from tests.base_test import BaseTest

from crc import app, db, session
from crc.models.approval import ApprovalModel, ApprovalSchema, ApprovalStatus


APPROVAL_PAYLOAD = {
    'id': None,
    'approver': {
      'uid': 'bgb22',
      'display_name': 'Billy Bob (bgb22)',
      'title': 'E42:He\'s a hoopy frood',
      'department': 'E0:EN-Eng Study of Parallel Universes'
    },
    'title': 'El Study',
    'status': 'DECLINED',
    'version': 1,
    'message': 'Incorrect documents',
    'associated_files': [
      {
        'id': 42,
        'name': 'File 1',
        'content_type': 'document'
      },
      {
        'id': 43,
        'name': 'File 2',
        'content_type': 'document'
      }
    ],
    'workflow_id': 1,
    'study_id': 1
}


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
            approver_uid='arc93',
            status=ApprovalStatus.PENDING.value,
            version=1
        )
        session.add(self.approval)

        self.approval_2 = ApprovalModel(
            study=self.study,
            workflow=self.workflow,
            approver_uid='dhf8r',
            status=ApprovalStatus.PENDING.value,
            version=1
        )
        session.add(self.approval_2)

        session.commit()

    def test_list_approvals_per_approver(self):
        """Only approvals associated with approver should be returned"""
        approver_uid = self.approval_2.approver_uid
        rv = self.app.get(f'/v1.0/approval', headers=self.logged_in_headers())
        self.assert_success(rv)

        response = json.loads(rv.get_data(as_text=True))

        # Stored approvals are 2
        approvals_count = ApprovalModel.query.count()
        self.assertEqual(approvals_count, 2)

        # but Dan's approvals should be only 1
        self.assertEqual(len(response), 1)

        # Confirm approver UID matches returned payload
        approval = ApprovalSchema().load(response[0])
        self.assertEqual(approval.approver['uid'], approver_uid)

    def test_list_approvals_per_admin(self):
        """All approvals will be returned"""
        rv = self.app.get('/v1.0/approval?everything=true', headers=self.logged_in_headers())
        self.assert_success(rv)

        response = json.loads(rv.get_data(as_text=True))

        # Returned approvals should match what's in the db
        approvals_count = ApprovalModel.query.count()
        response_count = len(response)
        self.assertEqual(2, response_count)

        rv = self.app.get('/v1.0/approval', headers=self.logged_in_headers())
        self.assert_success(rv)
        response_count = len(response)
        self.assertEqual(1, response_count)




    def test_update_approval(self):
        """Approval status will be updated"""
        approval_id = self.approval.id
        data = dict(APPROVAL_PAYLOAD)
        data['id'] = approval_id

        self.assertEqual(self.approval.status, ApprovalStatus.PENDING.value)

        rv = self.app.put(f'/v1.0/approval/{approval_id}',
                          content_type="application/json",
                          headers=self.logged_in_headers(),
                          data=json.dumps(data))
        self.assert_success(rv)

        session.refresh(self.approval)

        # Updated record should now have the data sent to the endpoint
        self.assertEqual(self.approval.message, data['message'])
        self.assertEqual(self.approval.status, ApprovalStatus.DECLINED.value)
