from tests.base_test import BaseTest
from crc import mail
from crc.models.email import EmailModel
import datetime
from unittest.mock import patch


class TestEmailScript(BaseTest):

    def test_do_task(self):
        workflow = self.create_workflow('email')

        task_data = {
          'PIComputingID': 'dhf8r@virginia.edu',
          'ApprvlApprvr1': 'lb3dp@virginia.edu'
        }
        task = self.get_workflow_api(workflow).next_task

        with mail.record_messages() as outbox:

            workflow_api = self.complete_form(workflow, task, task_data)

            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, 'Camunda Email Subject')

            # PI is present
            self.assertIn(task_data['PIComputingID'], outbox[0].body)
            self.assertIn(task_data['PIComputingID'], outbox[0].html)

            # Approver is present
            self.assertIn(task_data['ApprvlApprvr1'], outbox[0].body)
            self.assertIn(task_data['ApprvlApprvr1'], outbox[0].html)

            # Test nl2br formatting
            self.assertIn('<strong>Test Some Formatting</strong><br />', outbox[0].html)

            # Correct From field
            self.assertEqual('uvacrconnect@virginia.edu', outbox[0].sender)

            # Make sure we log the email
            # Grab model for comparison below
            db_emails = EmailModel.query.all()
            self.assertEqual(len(db_emails), 1)

            # Check whether we get a good email model back from the script
            self.assertIn('email_model', workflow_api.next_task.data)
            self.assertEqual(db_emails[0].recipients, workflow_api.next_task.data['email_model']['recipients'])
            self.assertEqual(db_emails[0].sender, workflow_api.next_task.data['email_model']['sender'])
            self.assertEqual(db_emails[0].subject, workflow_api.next_task.data['email_model']['subject'])

    @patch('crc.services.email_service.EmailService.add_email')
    def test_email_raises_exception(self, mock_response):
        self.load_example_data()
        mock_response.return_value.ok = True
        mock_response.side_effect = Exception("This is my exception!")

        workflow = self.create_workflow('email')

        task_data = {
          'PIComputingID': 'dhf8r@virginia.edu',
          'ApprvlApprvr1': 'lb3dp@virginia.edu'
        }
        task = self.get_workflow_api(workflow).next_task

        with mail.record_messages() as outbox:
            with self.assertRaises(Exception) as e:
                self.complete_form(workflow, task, task_data)

    def test_email_with_none_attachment(self):
        # This workflow specifically sends `attachments = None` as a parameter
        # to the email script
        workflow = self.create_workflow('email_none_attachment')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        with mail.record_messages() as outbox:
            workflow_api = self.complete_form(workflow, task, {'subject': 'My Test Email',
                                                               'recipients': 'user@example.com'})
            task = workflow_api.next_task
            # Make sure 'attachments' is in task.data, and is None
            self.assertIn('attachments', task.data)
            self.assertEqual(task.data['attachments'], None)

            # Make sure we still send an email
            self.assertIn('email_id', task.data)

            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, "My Test Email")
            self.assertEqual(outbox[0].recipients, ['user@example.com'])

    def test_email_attachment_empty_string(self):
        # This workflow specifically sends `attachments = ''` as a parameter
        # to the email script
        workflow = self.create_workflow('email_attachment_empty_string')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        with mail.record_messages() as outbox:
            workflow_api = self.complete_form(workflow, task, {'subject': 'My Test Email',
                                                               'recipients': 'user@example.com'})
            task = workflow_api.next_task
            # Make sure 'attachments' is in task.data, and is None
            self.assertIn('attachments', task.data)
            self.assertEqual(task.data['attachments'], '')

            # Make sure we still send an email
            self.assertIn('email_id', task.data)

            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, "My Test Email")
            self.assertEqual(outbox[0].recipients, ['user@example.com'])
