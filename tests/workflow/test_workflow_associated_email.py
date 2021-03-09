from tests.base_test import BaseTest
from crc import mail


class TestAssociatedEmail(BaseTest):

    def test_associated_email(self):
        # Only dhf8r is in testing DB.
        # We want to test multiple associates, and lb3dp is already in testing LDAP
        self.create_user(uid='lb3dp', email='lb3dp@virginia.edu', display_name='Laura Barnes')
        with mail.record_messages() as outbox:
            workflow = self.create_workflow('associated_email')
            workflow_api = self.get_workflow_api(workflow)
            # The workflow has a script task that adds two associates to the study; dhf8r and lb3dp
            first_task = workflow_api.next_task
            # This should send an email to both dhf8r and lb3dp
            self.complete_form(workflow_api, first_task, {})
            self.assertIn(outbox[0].recipients[0], ['dhf8r@virginia.edu', 'lb3dp@virginia.edu'])
            self.assertIn(outbox[0].recipients[1], ['dhf8r@virginia.edu', 'lb3dp@virginia.edu'])
