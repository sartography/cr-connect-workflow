from tests.base_test import BaseTest
from crc import mail, session
from crc.models.study import StudyModel
from crc.services.study_service import StudyService
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

            self.complete_form(workflow, first_task, {'subject': 'My Email Subject', 'recipients': 'test@example.com'})

            self.assertEqual(1, len(outbox))
            self.assertEqual('My Email Subject', outbox[0].subject)
            self.assertEqual(['test@example.com'], outbox[0].recipients)
            self.assertIn('Thank you for using this email example', outbox[0].body)

    def test_email_script_multiple(self):
        with mail.record_messages() as outbox:

            workflow = self.create_workflow('email_script')
            workflow_api = self.get_workflow_api(workflow)
            first_task = workflow_api.next_task

            self.complete_form(workflow, first_task, {'subject': 'My Email Subject', 'recipients': ['test@example.com', 'test2@example.com']})

            self.assertEqual(1, len(outbox))
            self.assertEqual("My Email Subject", outbox[0].subject)
            self.assertEqual(2, len(outbox[0].recipients))
            self.assertEqual('test@example.com', outbox[0].recipients[0])
            self.assertEqual('test2@example.com', outbox[0].recipients[1])

    def test_bad_email_address_1(self):
        workflow = self.create_workflow('email_script')
        first_task = self.get_workflow_api(workflow).next_task

        with self.assertRaises(AssertionError):
            self.complete_form(workflow, first_task, {'recipients': 'test@example'})

    def test_bad_email_address_2(self):
        workflow = self.create_workflow('email_script')
        first_task = self.get_workflow_api(workflow).next_task

        with self.assertRaises(AssertionError):
            self.complete_form(workflow, first_task, {'recipients': 'test'})

    def test_email_script_associated(self):
        workflow = self.create_workflow('email_script')
        workflow_api = self.get_workflow_api(workflow)

        # Only dhf8r is in testing DB.
        # We want to test multiple associates, and lb3dp is already in testing LDAP
        self.create_user(uid='lb3dp', email='lb3dp@virginia.edu', display_name='Laura Barnes')
        StudyService.update_study_associates(workflow.study_id,
                                             [{'uid': 'dhf8r', 'role': 'Chief Bee Keeper', 'send_email': True, 'access': True},
                                              {'uid': 'lb3dp', 'role': 'Chief Cat Herder', 'send_email': True, 'access': True}])

        first_task = workflow_api.next_task

        with mail.record_messages() as outbox:
            self.complete_form(workflow, first_task, {'subject': 'My Test Subject', 'recipients': ['user@example.com', 'associated']})

            self.assertEqual(1, len(outbox))
            self.assertIn(outbox[0].recipients[0], ['user@example.com', 'dhf8r@virginia.edu', 'lb3dp@virginia.edu'])
            self.assertIn(outbox[0].recipients[1], ['user@example.com', 'dhf8r@virginia.edu', 'lb3dp@virginia.edu'])
            self.assertIn(outbox[0].recipients[2], ['user@example.com', 'dhf8r@virginia.edu', 'lb3dp@virginia.edu'])

    def test_email_script_cc(self):
        workflow = self.create_workflow('email_script')
        workflow_api = self.get_workflow_api(workflow)
        self.create_user(uid='lb3dp', email='lb3dp@virginia.edu', display_name='Laura Barnes')
        StudyService.update_study_associates(workflow.study_id,
                                             [{'uid': 'dhf8r', 'role': 'Chief Bee Keeper', 'send_email': True, 'access': True},
                                              {'uid': 'lb3dp', 'role': 'Chief Cat Herder', 'send_email': True, 'access': True}])
        first_task = workflow_api.next_task
        with mail.record_messages() as outbox:

            self.complete_form(workflow, first_task, {'subject': 'My Test Subject', 'recipients': 'user@example.com', 'cc': 'associated'})

            self.assertEqual(1, len(outbox))
            self.assertEqual('user@example.com', outbox[0].recipients[0])
            self.assertIn(outbox[0].cc[0], ['dhf8r@virginia.edu', 'lb3dp@virginia.edu'])
            self.assertIn(outbox[0].cc[1], ['dhf8r@virginia.edu', 'lb3dp@virginia.edu'])
