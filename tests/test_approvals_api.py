import json
import random
import string

from tests.base_test import BaseTest
from crc import session, db
from crc.models.approval import ApprovalModel, ApprovalStatus
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowModel


class TestApprovals(BaseTest):
    def setUp(self):
        """Initial setup shared by all TestApprovals tests"""
        self.load_example_data()

        # Add a study with 2 approvers
        study_workflow_approvals_1 = self._create_study_workflow_approvals(
            user_uid="dhf8r", title="first study", primary_investigator_id="lb3dp",
            approver_uids=["lb3dp", "dhf8r"], statuses=[ApprovalStatus.PENDING.value, ApprovalStatus.PENDING.value]
        )
        self.study = study_workflow_approvals_1['study']
        self.workflow = study_workflow_approvals_1['workflow']
        self.approval = study_workflow_approvals_1['approvals'][0]
        self.approval_2 = study_workflow_approvals_1['approvals'][1]

        # Add a study with 1 approver
        study_workflow_approvals_2 = self._create_study_workflow_approvals(
            user_uid="dhf8r", title="second study", primary_investigator_id="dhf8r",
            approver_uids=["lb3dp"], statuses=[ApprovalStatus.PENDING.value]
        )
        self.unrelated_study = study_workflow_approvals_2['study']
        self.unrelated_workflow = study_workflow_approvals_2['workflow']
        self.approval_3 = study_workflow_approvals_2['approvals'][0]

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

    def test_list_approvals_as_user(self):
        """All approvals as different user"""
        rv = self.app.get('/v1.0/approval?as_user=lb3dp', headers=self.logged_in_headers())
        self.assert_success(rv)

        response = json.loads(rv.get_data(as_text=True))

        # Returned approvals should match what's in the db for user ld3dp, we should get one
        # approval back per study (2 studies), and that approval should have one related approval.
        response_count = len(response)
        self.assertEqual(2, response_count)

        rv = self.app.get('/v1.0/approval', headers=self.logged_in_headers())
        self.assert_success(rv)
        response = json.loads(rv.get_data(as_text=True))
        response_count = len(response)
        self.assertEqual(1, response_count)
        self.assertEqual(1, len(response[0]['related_approvals']))  # this approval has a related approval.

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
                "approver": {"uid": "dhf8r"},
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
                "approver": {"uid": "dhf8r"},
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

    def test_csv_export(self):
        self.load_test_spec('two_forms')
        self._add_lots_of_random_approvals(n=50, workflow_spec_name='two_forms')

        # Get all workflows
        workflows = db.session.query(WorkflowModel).filter_by(workflow_spec_id='two_forms').all()

        # For each workflow, complete all tasks
        for workflow in workflows:
            workflow_api = self.get_workflow_api(workflow, user_uid=workflow.study.user_uid)
            self.assertEqual('two_forms', workflow_api.workflow_spec_id)

            # Log current user out.
            self.flask_globals.user = None
            self.assertIsNone(self.flask_globals.user)

            # Complete the form for Step one and post it.
            self.complete_form(workflow, workflow_api.next_task, {"color": "blue"}, error_code=None, user_uid=workflow.study.user_uid)

            # Get the next Task
            workflow_api = self.get_workflow_api(workflow, user_uid=workflow.study.user_uid)
            self.assertEqual("StepTwo", workflow_api.next_task.name)

            # Get all user Tasks and check that the data have been saved
            task = workflow_api.next_task
            self.assertIsNotNone(task.data)
            for val in task.data.values():
                self.assertIsNotNone(val)

        rv = self.app.get(f'/v1.0/approval/csv', headers=self.logged_in_headers())
        self.assert_success(rv)

    def test_all_approvals(self):
        self._add_lots_of_random_approvals()

        not_canceled = session.query(ApprovalModel).filter(ApprovalModel.status != 'CANCELED').all()
        not_canceled_study_ids = []
        for a in not_canceled:
            if a.study_id not in not_canceled_study_ids:
                not_canceled_study_ids.append(a.study_id)

        rv_all = self.app.get(f'/v1.0/all_approvals?status=false', headers=self.logged_in_headers())
        self.assert_success(rv_all)
        all_data = json.loads(rv_all.get_data(as_text=True))
        self.assertEqual(len(all_data), len(not_canceled_study_ids), 'Should return all non-canceled approvals, grouped by study')

        all_approvals = session.query(ApprovalModel).all()
        all_approvals_study_ids = []
        for a in all_approvals:
            if a.study_id not in all_approvals_study_ids:
                all_approvals_study_ids.append(a.study_id)

        rv_all = self.app.get(f'/v1.0/all_approvals?status=true', headers=self.logged_in_headers())
        self.assert_success(rv_all)
        all_data = json.loads(rv_all.get_data(as_text=True))
        self.assertEqual(len(all_data), len(all_approvals_study_ids), 'Should return all approvals, grouped by study')

    def test_approvals_counts(self):
        statuses = [name for name, value in ApprovalStatus.__members__.items()]
        self._add_lots_of_random_approvals()

        # Get the counts
        rv_counts = self.app.get(f'/v1.0/approval-counts', headers=self.logged_in_headers())
        self.assert_success(rv_counts)
        counts = json.loads(rv_counts.get_data(as_text=True))

        # Get the actual approvals
        rv_approvals = self.app.get(f'/v1.0/approval', headers=self.logged_in_headers())
        self.assert_success(rv_approvals)
        approvals = json.loads(rv_approvals.get_data(as_text=True))

        # Tally up the number of approvals in each status category
        manual_counts = {}
        for status in statuses:
            manual_counts[status] = 0

        for approval in approvals:
            manual_counts[approval['status']] += 1

        # Numbers in each category should match
        for status in statuses:
            self.assertEqual(counts[status], manual_counts[status], 'Approval counts for status %s should match' % status)

        # Total number of approvals should match
        total_counts = sum(counts[status] for status in statuses)
        self.assertEqual(total_counts, len(approvals), 'Total approval counts for user should match number of approvals for user')

    def _create_study_workflow_approvals(self, user_uid, title, primary_investigator_id, approver_uids, statuses,
                                         workflow_spec_name="random_fact"):
        study = self.create_study(uid=user_uid, title=title, primary_investigator_id=primary_investigator_id)
        workflow = self.create_workflow(workflow_name=workflow_spec_name, study=study)
        approvals = []

        for i in range(len(approver_uids)):
            approvals.append(self.create_approval(
                study=study,
                workflow=workflow,
                approver_uid=approver_uids[i],
                status=statuses[i],
                version=1
            ))

        return {
            'study': study,
            'workflow': workflow,
            'approvals': approvals,
        }

    def _add_lots_of_random_approvals(self, n=100, workflow_spec_name="random_fact"):
        num_studies_before = db.session.query(StudyModel).count()
        statuses = [name for name, value in ApprovalStatus.__members__.items()]

        # Add a whole bunch of approvals with random statuses
        for i in range(n):
            approver_uids = random.choices(["lb3dp", "dhf8r"])
            self._create_study_workflow_approvals(
                user_uid=random.choice(["lb3dp", "dhf8r"]),
                title="".join(random.choices(string.ascii_lowercase, k=64)),
                primary_investigator_id=random.choice(["lb3dp", "dhf8r"]),
                approver_uids=approver_uids,
                statuses=random.choices(statuses, k=len(approver_uids)),
                workflow_spec_name=workflow_spec_name
            )

        session.flush()
        num_studies_after = db.session.query(StudyModel).count()
        self.assertEqual(num_studies_after, num_studies_before + n)

