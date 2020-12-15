from tests.base_test import BaseTest
from crc import mail


# class TestEmailDirectly(BaseTest):
#
#     def test_email_directly(self):
#         recipients = ['michaelc@cullerton.com']
#         sender = 'michaelc@cullerton.com'
#         with mail.record_messages() as outbox:
#             mail.send_message(subject='testing',
#                               body='test',
#                               recipients=recipients,
#                               sender=sender)
#             assert len(outbox) == 1
#             assert outbox[0].subject == "testing"


class TestEmailScript(BaseTest):

    def test_email_script(self):
        with mail.record_messages() as outbox:

            workflow = self.create_workflow('email_script')

            first_task = self.get_workflow_api(workflow).next_task

            workflow = self.get_workflow_api(workflow)
            self.complete_form(workflow, first_task, {'email_address': 'test@example.com'})

            self.assertEqual(1, len(outbox))
            self.assertEqual('My Email Subject', outbox[0].subject)
            self.assertEqual(['test@example.com'], outbox[0].recipients)

    def test_email_script_multiple(self):
        with mail.record_messages() as outbox:

            workflow = self.create_workflow('email_script')

            first_task = self.get_workflow_api(workflow).next_task

            workflow = self.get_workflow_api(workflow)
            self.complete_form(workflow, first_task, {'email_address': ['test@example.com', 'test2@example.com']})

            self.assertEqual(1, len(outbox))
            self.assertEqual("My Email Subject", outbox[0].subject)
            self.assertEqual(2, len(outbox[0].recipients))
            self.assertEqual('test@example.com', outbox[0].recipients[0])
            self.assertEqual('test2@example.com', outbox[0].recipients[1])

    def test_bad_email_address_1(self):
        workflow = self.create_workflow('email_script')

        first_task = self.get_workflow_api(workflow).next_task

        workflow = self.get_workflow_api(workflow)
        with self.assertRaises(AssertionError):
            self.complete_form(workflow, first_task, {'email_address': 'test@example'})


    def test_bad_email_address_2(self):
        workflow = self.create_workflow('email_script')

        first_task = self.get_workflow_api(workflow).next_task

        workflow = self.get_workflow_api(workflow)
        with self.assertRaises(AssertionError):
            self.complete_form(workflow, first_task, {'email_address': 'test'})
