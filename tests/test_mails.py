
from tests.base_test import BaseTest

from crc import mail, session
from crc.models.approval import ApprovalModel, ApprovalStatus
from crc.services.mails import (
    send_ramp_up_submission_email,
    send_ramp_up_approval_request_email,
    send_ramp_up_approval_request_first_review_email,
    send_ramp_up_approved_email,
    send_ramp_up_denied_email,
    send_ramp_up_denied_email_to_approver
)


class TestMails(BaseTest):

    def setUp(self):
        """Initial setup shared by all TestApprovals tests"""
        self.load_example_data()
        self.study = self.create_study()
        self.workflow = self.create_workflow('random_fact')

        self.approval = ApprovalModel(
            study=self.study,
            workflow=self.workflow,
            approver_uid='lb3dp',
            status=ApprovalStatus.PENDING.value,
            version=1
        )
        session.add(self.approval)
        session.commit()

        self.sender = 'sender@sartography.com'
        self.recipients = ['recipient@sartography.com']
        self.primary_investigator = 'Dr. Bartlett'
        self.approver_1 = 'Max Approver'
        self.approver_2 = 'Close Reviewer'

    def test_send_ramp_up_submission_email(self):
        with mail.record_messages() as outbox:

            send_ramp_up_submission_email(self.sender, self.recipients, self.approval.id, self.approver_1)
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, 'Research Ramp-up Plan Submitted')
            self.assertIn(self.approver_1, outbox[0].body)
            self.assertIn(self.approver_1, outbox[0].html)

            send_ramp_up_submission_email(self.sender, self.recipients, self.approval.id,
                                          self.approver_1, self.approver_2)
            self.assertEqual(len(outbox), 2)
            self.assertIn(self.approver_1, outbox[1].body)
            self.assertIn(self.approver_1, outbox[1].html)
            self.assertIn(self.approver_2, outbox[1].body)
            self.assertIn(self.approver_2, outbox[1].html)

    def test_send_ramp_up_approval_request_email(self):
        with mail.record_messages() as outbox:
            send_ramp_up_approval_request_email(self.sender, self.recipients, self.approval.id,
                                                self.primary_investigator)

            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, 'Research Ramp-up Plan Approval Request')
            self.assertIn(self.primary_investigator, outbox[0].body)
            self.assertIn(self.primary_investigator, outbox[0].html)

    def test_send_ramp_up_approval_request_first_review_email(self):
        with mail.record_messages() as outbox:
            send_ramp_up_approval_request_first_review_email(
                self.sender, self.recipients, self.approval.id, self.primary_investigator
            )

            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, 'Research Ramp-up Plan Approval Request')
            self.assertIn(self.primary_investigator, outbox[0].body)
            self.assertIn(self.primary_investigator, outbox[0].html)

    def test_send_ramp_up_approved_email(self):
        with mail.record_messages() as outbox:
            send_ramp_up_approved_email(self.sender, self.recipients, self.approval.id, self.approver_1)
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, 'Research Ramp-up Plan Approved')
            self.assertIn(self.approver_1, outbox[0].body)
            self.assertIn(self.approver_1, outbox[0].html)

            send_ramp_up_approved_email(self.sender, self.recipients, self.approval.id,
                                        self.approver_1, self.approver_2)
            self.assertEqual(len(outbox), 2)
            self.assertIn(self.approver_1, outbox[1].body)
            self.assertIn(self.approver_1, outbox[1].html)
            self.assertIn(self.approver_2, outbox[1].body)
            self.assertIn(self.approver_2, outbox[1].html)

    def test_send_ramp_up_denied_email(self):
        with mail.record_messages() as outbox:
            send_ramp_up_denied_email(self.sender, self.recipients, self.approval.id, self.approver_1)
            self.assertEqual(outbox[0].subject, 'Research Ramp-up Plan Denied')
            self.assertIn(self.approver_1, outbox[0].body)
            self.assertIn(self.approver_1, outbox[0].html)

    def test_send_send_ramp_up_denied_email_to_approver(self):
        with mail.record_messages() as outbox:
            send_ramp_up_denied_email_to_approver(
                self.sender, self.recipients, self.approval.id, self.primary_investigator, self.approver_2
            )

            self.assertEqual(outbox[0].subject, 'Research Ramp-up Plan Denied')
            self.assertIn(self.primary_investigator, outbox[0].body)
            self.assertIn(self.primary_investigator, outbox[0].html)
            self.assertIn(self.approver_2, outbox[0].body)
            self.assertIn(self.approver_2, outbox[0].html)
