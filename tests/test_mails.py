
from tests.base_test import BaseTest

from crc.services.mails import (
    send_ramp_up_submission_email,
    send_ramp_up_approval_request_email,
    send_ramp_up_approval_request_first_review_email,
    send_ramp_up_approved_email,
    send_ramp_up_denied_email
)


class TestMails(BaseTest):

    def setUp(self):
        self.sender = 'sender@sartography.com'
        self.recipients = ['recipient@sartography.com']
        self.primary_investigator = 'Dr. Bartlett'
        self.approver_1 = 'Max Approver'
        self.approver_2 = 'Close Reviewer'

    def test_send_ramp_up_submission_email(self):
        send_ramp_up_submission_email(self.sender, self.recipients, self.approver_1)
        self.assertTrue(True)

        send_ramp_up_submission_email(self.sender, self.recipients, self.approver_1)
        self.assertTrue(True)

    def test_send_ramp_up_approval_request_email(self):
        send_ramp_up_approval_request_email(self.sender, self.recipients, self.primary_investigator)
        self.assertTrue(True)

    def test_send_ramp_up_approval_request_first_review_email(self):
        send_ramp_up_approval_request_first_review_email(
            self.sender, self.recipients, self.primary_investigator, self.approver_1
        )
        self.assertTrue(True)

    def test_send_ramp_up_approved_email(self):
        send_ramp_up_approved_email(self.sender, self.recipients, self.approver_1)
        self.assertTrue(True)

        send_ramp_up_approved_email(self.sender, self.recipients, self.approver_1, self.approver_2)
        self.assertTrue(True)

    def test_send_ramp_up_denied_email(self):
        send_ramp_up_denied_email(self.sender, self.recipients, self.approver_1)
        self.assertTrue(True)
