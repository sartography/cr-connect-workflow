from tests.base_test import BaseTest
from crc import mail, session
from crc.models.email import EmailModel
from crc.services.study_service import StudyService
from crc.services.user_file_service import UserFileService


class TestEmailScript(BaseTest):

    def test_email_script_validation(self):
        # This validates scripts.email.do_task_validate_only
        # It also tests that we don't overwrite the default email_address with random text during validation
        # Otherwise json would have an error about parsing the email address
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('email_script')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)

    def test_email_script(self):
        with mail.record_messages() as outbox:

            workflow = self.create_workflow('email_script')
            first_task = self.get_workflow_api(workflow).next_task
            workflow_api = self.complete_form(workflow, first_task, {'subject': 'My Email Subject', 'recipients': 'test@example.com',
                                                                     'cc': 'cc@example.com', 'bcc': 'bcc@example.com',
                                                                     'reply_to': 'reply_to@example.com', 'name': 'My Email Name'})
            task = workflow_api.next_task
            email_id = task.data['email_model']['id']

            self.assertEqual(1, len(outbox))
            self.assertEqual('My Email Subject', outbox[0].subject)
            self.assertEqual(['test@example.com'], outbox[0].recipients)
            self.assertEqual(['cc@example.com'], outbox[0].cc)
            self.assertEqual(['bcc@example.com'], outbox[0].bcc)
            self.assertEqual('reply_to@example.com', outbox[0].reply_to)
            self.assertIn('Thank you for using this email example', outbox[0].body)

            email_name = session.query(EmailModel.name).filter(EmailModel.id == email_id).scalar()
            self.assertEqual('My Email Name', email_name)

    def test_email_script_multiple(self):
        self.create_reference_document()
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

    def test_email_script_attachments(self):
        self.create_reference_document()
        irb_code_1 = 'Study_App_Doc'
        irb_code_2 = 'Study_Protocol_Document'

        workflow = self.create_workflow('email_script')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name=first_task.name,
                                          name="something.png", content_type="text",
                                          binary_data=b'1234', irb_doc_code=irb_code_1)
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name=first_task.name,
                                          name="another.png", content_type="text",
                                          binary_data=b'67890', irb_doc_code=irb_code_1)
        UserFileService.add_workflow_file(workflow_id=workflow.id,
                                          task_spec_name=first_task.name,
                                          name="anything.png", content_type="text",
                                          binary_data=b'5678', irb_doc_code=irb_code_2)

        with mail.record_messages() as outbox:
            self.complete_form(workflow, first_task, {'subject': 'My Test Subject', 'recipients': 'user@example.com',
                                                      'doc_codes': [{'doc_code': irb_code_1}, {'doc_code': irb_code_2}]})
            self.assertEqual(1, len(outbox))
            self.assertEqual(3, len(outbox[0].attachments))
            self.assertEqual('image/png', outbox[0].attachments[0].content_type)
            self.assertEqual('something.png', outbox[0].attachments[0].filename)
            self.assertEqual(b'1234', outbox[0].attachments[0].data)
