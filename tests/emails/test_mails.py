from crc import mail
from crc.models.email import EmailModel
from crc.services.mails import (
    send_ramp_up_submission_email,
    send_ramp_up_approval_request_email,
    send_ramp_up_approval_request_first_review_email,
    send_ramp_up_approved_email,
    send_ramp_up_denied_email,
    send_ramp_up_denied_email_to_approver
)
from tests.base_test import BaseTest


class TestMails(BaseTest):

    def setUp(self):
        """Initial setup shared by all TestApprovals tests"""
        self.load_example_data()
        self.study = self.create_study()
        self.workflow = self.create_workflow('random_fact')

        self.sender = 'sender@sartography.com'
        self.recipients = ['recipient@sartography.com']
        self.primary_investigator = 'Dr. Bartlett'
        self.approver_1 = 'Max Approver'
        self.approver_2 = 'Close Reviewer'

    def test_send_ramp_up_submission_email(self):
        with mail.record_messages() as outbox:
            send_ramp_up_submission_email(self.sender, self.recipients, self.approver_1)
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, 'Research Ramp-up Plan Submitted')
            self.assertIn(self.approver_1, outbox[0].body)
            self.assertIn(self.approver_1, outbox[0].html)

            send_ramp_up_submission_email(self.sender, self.recipients, self.approver_1, self.approver_2)
            self.assertEqual(len(outbox), 2)
            self.assertIn(self.approver_1, outbox[1].body)
            self.assertIn(self.approver_1, outbox[1].html)
            self.assertIn(self.approver_2, outbox[1].body)
            self.assertIn(self.approver_2, outbox[1].html)

            db_emails = EmailModel.query.count()
            self.assertEqual(db_emails, 2)

    def test_send_ramp_up_approval_request_email(self):
        with mail.record_messages() as outbox:
            send_ramp_up_approval_request_email(self.sender, self.recipients, self.primary_investigator)

            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, 'Research Ramp-up Plan Approval Request')
            self.assertIn(self.primary_investigator, outbox[0].body)
            self.assertIn(self.primary_investigator, outbox[0].html)

            db_emails = EmailModel.query.count()
            self.assertEqual(db_emails, 1)

    def test_send_ramp_up_approval_request_first_review_email(self):
        with mail.record_messages() as outbox:
            send_ramp_up_approval_request_first_review_email(
                self.sender, self.recipients, self.primary_investigator
            )

            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, 'Research Ramp-up Plan Approval Request')
            self.assertIn(self.primary_investigator, outbox[0].body)
            self.assertIn(self.primary_investigator, outbox[0].html)

            db_emails = EmailModel.query.count()
            self.assertEqual(db_emails, 1)

    def test_send_ramp_up_approved_email(self):
        with mail.record_messages() as outbox:
            send_ramp_up_approved_email(self.sender, self.recipients, self.approver_1)
            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, 'Research Ramp-up Plan Approved')
            self.assertIn(self.approver_1, outbox[0].body)
            self.assertIn(self.approver_1, outbox[0].html)

            send_ramp_up_approved_email(self.sender, self.recipients, self.approver_1, self.approver_2)
            self.assertEqual(len(outbox), 2)
            self.assertIn(self.approver_1, outbox[1].body)
            self.assertIn(self.approver_1, outbox[1].html)
            self.assertIn(self.approver_2, outbox[1].body)
            self.assertIn(self.approver_2, outbox[1].html)

            db_emails = EmailModel.query.count()
            self.assertEqual(db_emails, 2)

    def test_send_ramp_up_denied_email(self):
        with mail.record_messages() as outbox:
            send_ramp_up_denied_email(self.sender, self.recipients, self.approver_1)
            self.assertEqual(outbox[0].subject, 'Research Ramp-up Plan Denied')
            self.assertIn(self.approver_1, outbox[0].body)
            self.assertIn(self.approver_1, outbox[0].html)

            db_emails = EmailModel.query.count()
            self.assertEqual(db_emails, 1)

    def test_send_send_ramp_up_denied_email_to_approver(self):
        with mail.record_messages() as outbox:
            send_ramp_up_denied_email_to_approver(
                self.sender, self.recipients, self.primary_investigator, self.approver_2
            )

            self.assertEqual(outbox[0].subject, 'Research Ramp-up Plan Denied')
            self.assertIn(self.primary_investigator, outbox[0].body)
            self.assertIn(self.primary_investigator, outbox[0].html)
            self.assertIn(self.approver_2, outbox[0].body)
            self.assertIn(self.approver_2, outbox[0].html)

            db_emails = EmailModel.query.count()
            self.assertEqual(db_emails, 1)
