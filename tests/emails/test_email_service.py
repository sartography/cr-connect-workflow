from tests.base_test import BaseTest

from crc import session
from crc.models.email import EmailModel
from crc.services.email_service import EmailService
from unittest.mock import patch


class TestEmailService(BaseTest):

    def test_add_email(self):
        study = self.create_study()

        subject = 'Email Subject'
        sender = 'sender@sartography.com'
        recipients = ['recipient@sartography.com', 'back@sartography.com']
        content = 'Content for this email'
        content_html = '<p>Hypertext Markup Language content for this email</p>'

        EmailService.add_email(subject=subject, sender=sender, recipients=recipients,
                               content=content, content_html=content_html, study_id=study.id)

        email_model = EmailModel.query.first()

        self.assertEqual(email_model.subject, subject)
        self.assertEqual(email_model.sender, sender)
        self.assertEqual(email_model.recipients, str(recipients))
        self.assertEqual(email_model.content, content)
        self.assertEqual(email_model.content_html, content_html)
        self.assertEqual(email_model.study, study)

        subject = 'Email Subject - Empty study'
        EmailService.add_email(subject=subject, sender=sender, recipients=recipients,
                               content=content, content_html=content_html)

        email_model = EmailModel.query.order_by(EmailModel.id.desc()).first()

        self.assertEqual(email_model.subject, subject)
        self.assertEqual(email_model.sender, sender)
        self.assertEqual(email_model.recipients, str(recipients))
        self.assertEqual(email_model.content, content)
        self.assertEqual(email_model.content_html, content_html)
        self.assertEqual(email_model.study, None)

    @patch('crc.services.email_service.EmailService.add_email')
    def test_add_email_with_error(self, mock_response):

        mock_response.return_value.ok = True
        mock_response.side_effect = Exception("This is my exception!")

        study = self.create_study()

        subject = 'Email Subject'
        sender = 'sender@sartography.com'
        recipients = ['recipient@sartography.com', 'back@sartography.com']
        content = 'Content for this email'
        content_html = '<p>Hypertext Markup Language content for this email</p>'

        # Make sure we generate an error
        with self.assertRaises(Exception) as e:
            EmailService.add_email(subject=subject, sender=sender, recipients=recipients,
                                   content=content, content_html=content_html, study_id=study.id)
        # Make sure it's the error we want
        self.assertEqual('This is my exception!', e.exception.args[0])
