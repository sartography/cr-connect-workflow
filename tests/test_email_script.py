from tests.base_test import BaseTest
from crc import mail
import json


class TestEmailScript(BaseTest):

    def test_email_script_validation(self):
        # This validates scripts.email.do_task_validate_only
        # It also tests that we don't overwrite the default email_address with random text during validation
        # Otherwise json would have an error about parsing the email address
        self.load_example_data()
        spec_model = self.load_test_spec('email_script')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)

    def test_email_script(self):
        with mail.record_messages() as outbox:

            workflow = self.create_workflow('email_script')

            first_task = self.get_workflow_api(workflow).next_task

            workflow = self.get_workflow_api(workflow)
            self.assertEqual('dan@sartography.com', workflow.next_task.data['email_address'])
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
