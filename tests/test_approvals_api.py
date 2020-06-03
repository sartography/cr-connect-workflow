import json
from tests.base_test import BaseTest

from crc import session
from crc.models.approval import ApprovalModel, ApprovalSchema, ApprovalStatus
from crc.models.protocol_builder import ProtocolBuilderStatus
from crc.models.study import StudyModel


class TestApprovals(BaseTest):
    def setUp(self):
        """Initial setup shared by all TestApprovals tests"""
        self.load_example_data()
        self.study = self.create_study()
        self.workflow = self.create_workflow('random_fact')
        self.unrelated_study = StudyModel(title="second study",
                                 protocol_builder_status=ProtocolBuilderStatus.ACTIVE,
                                 user_uid="dhf8r", primary_investigator_id="dhf8r")
        self.unrelated_workflow = self.create_workflow('random_fact', study=self.unrelated_study)

        # TODO: Move to base_test as a helper
        self.approval = ApprovalModel(
            study=self.study,
            workflow=self.workflow,
            approver_uid='lb3dp',
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

        # A third study, unrelated to the first.
        self.approval_3 = ApprovalModel(
            study=self.unrelated_study,
            workflow=self.unrelated_workflow,
            approver_uid='lb3dp',
            status=ApprovalStatus.PENDING.value,
            version=1
        )
        session.add(self.approval_3)

        session.commit()

    def test_list_approvals_per_approver(self):
        """Only approvals associated with approver should be returned"""
        approver_uid = self.approval_2.approver_uid
        rv = self.app.get(f'/v1.0/approval', headers=self.logged_in_headers())
        self.assert_success(rv)

        response = json.loads(rv.get_data(as_text=True))

        # Stored approvals are 3
        approvals_count = ApprovalModel.query.count()
        self.assertEqual(approvals_count, 3)

        # but Dan's approvals should be only 1
        self.assertEqual(len(response), 1)

        # Confirm approver UID matches returned payload
        approval = response[0]
        self.assertEqual(approval['approver']['uid'], approver_uid)

    def test_list_approvals_per_admin(self):
        """All approvals will be returned"""
        rv = self.app.get('/v1.0/approval?everything=true', headers=self.logged_in_headers())
        self.assert_success(rv)

        response = json.loads(rv.get_data(as_text=True))

        # Returned approvals should match what's in the db, we should get one approval back
        # per study (2 studies), and that approval should have one related approval.
        approvals_count = ApprovalModel.query.count()
        response_count = len(response)
        self.assertEqual(2, response_count)

        rv = self.app.get('/v1.0/approval', headers=self.logged_in_headers())
        self.assert_success(rv)
        response = json.loads(rv.get_data(as_text=True))
        response_count = len(response)
        self.assertEqual(1, response_count)
        self.assertEqual(1, len(response[0]['related_approvals'])) # this approval has a related approval.

    def test_update_approval_fails_if_not_the_approver(self):
        approval = session.query(ApprovalModel).filter_by(approver_uid='lb3dp').first()
        data = {'id': approval.id,
                "approver_uid": "dhf8r",
                'message': "Approved.  I like the cut of your jib.",
                'status': ApprovalStatus.APPROVED.value}

        self.assertEqual(approval.status, ApprovalStatus.PENDING.value)

        rv = self.app.put(f'/v1.0/approval/{approval.id}',
                          content_type="application/json",
                          headers=self.logged_in_headers(),  # As dhf8r
                          data=json.dumps(data))
        self.assert_failure(rv)

    def test_accept_approval(self):
        approval = session.query(ApprovalModel).filter_by(approver_uid='dhf8r').first()
        data = {'id': approval.id,
                "approver_uid": "dhf8r",
                'message': "Approved.  I like the cut of your jib.",
                'status': ApprovalStatus.APPROVED.value}

        self.assertEqual(approval.status, ApprovalStatus.PENDING.value)

        rv = self.app.put(f'/v1.0/approval/{approval.id}',
                          content_type="application/json",
                          headers=self.logged_in_headers(),  # As dhf8r
                          data=json.dumps(data))
        self.assert_success(rv)

        session.refresh(approval)

        # Updated record should now have the data sent to the endpoint
        self.assertEqual(approval.message, data['message'])
        self.assertEqual(approval.status, ApprovalStatus.APPROVED.value)

    def test_decline_approval(self):
        approval = session.query(ApprovalModel).filter_by(approver_uid='dhf8r').first()
        data = {'id': approval.id,
                "approver_uid": "dhf8r",
                'message': "Approved.  I find the cut of your jib lacking.",
                'status': ApprovalStatus.DECLINED.value}

        self.assertEqual(approval.status, ApprovalStatus.PENDING.value)

        rv = self.app.put(f'/v1.0/approval/{approval.id}',
                          content_type="application/json",
                          headers=self.logged_in_headers(),  # As dhf8r
                          data=json.dumps(data))
        self.assert_success(rv)

        session.refresh(approval)

        # Updated record should now have the data sent to the endpoint
        self.assertEqual(approval.message, data['message'])
        self.assertEqual(approval.status, ApprovalStatus.DECLINED.value)
