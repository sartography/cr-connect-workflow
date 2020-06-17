from tests.base_test import BaseTest

from crc import session
from crc.models.approval import ApprovalModel, ApprovalStatus
from crc.models.email import EmailModel
from crc.services.email_service import EmailService


class TestEmailService(BaseTest):

    def test_add_email(self):
        self.load_example_data()
        study = self.create_study()
        workflow = self.create_workflow('random_fact')

        approval = ApprovalModel(
            study=study,
            workflow=workflow,
            approver_uid='lb3dp',
            status=ApprovalStatus.PENDING.value,
            version=1
        )
        session.add(approval)
        session.commit()

        subject = 'Email Subject'
        sender = 'sender@sartography.com'
        recipients = ['recipient@sartography.com', 'back@sartography.com']
        content = 'Content for this email'
        content_html = '<p>Hypertext Markup Language content for this email</p>'

        EmailService.add_email(subject=subject, sender=sender, recipients=recipients,
                               content=content, content_html=content_html, approval_id=approval.id)

        email_model = EmailModel.query.first()

        self.assertEqual(email_model.subject, subject)
        self.assertEqual(email_model.sender, sender)
        self.assertEqual(email_model.recipients, str(recipients))
        self.assertEqual(email_model.content, content)
        self.assertEqual(email_model.content_html, content_html)
        self.assertEqual(email_model.approval, approval)
