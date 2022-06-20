from tests.base_test import BaseTest
from crc import mail, session
from crc.models.workflow import WorkflowModel
from crc.services.email_service import EmailService
from crc.services.user_file_service import UserFileService


class TestGetEmailData(BaseTest):

    def test_email_data_validation(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('get_email_data')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)

    def test_get_email_data_by_email_id(self):
        workflow = self.create_workflow('get_email_data')
        study = workflow.study
        with mail.record_messages() as outbox:
            # Send an email we can use for get_email_data
            email_model = EmailService.add_email(subject='My Email Subject',
                                                 sender='sender@example.com',
                                                 recipients=['joe@example.com'],
                                                 name='My Email Name',
                                                 content='asdf', content_html=None, study_id=study.id)

            workflow_api = self.get_workflow_api(workflow)
            task = workflow_api.next_task

            # Run workflow with get_email_data
            workflow_api = self.complete_form(workflow, task, {'email_id': email_model.id})

            # Make assertions
            task = workflow_api.next_task
            data = task.data
            self.assertIn('email_data', data)
            email_data = data['email_data']
            self.assertEqual(1, len(email_data))
            self.assertIn('doc_codes', email_data[0])
            self.assertEqual('My Email Subject', email_data[0]['subject'])
            self.assertEqual('sender@example.com', email_data[0]['sender'])
            self.assertEqual('[\'joe@example.com\']', email_data[0]['recipients'])
            self.assertEqual('My Email Name', email_data[0]['name'])
            # Make sure we remove content_html from email_data
            self.assertNotIn('content_html', email_data[0])

    def test_get_email_data_by_workflow_spec_id(self):
        workflow = self.create_workflow('get_email_data_by_workflow')
        study = workflow.study
        email_workflow = session.query(WorkflowModel).first()
        email_workflow_spec_id = email_workflow.workflow_spec_id

        with mail.record_messages() as outbox:
            # Send an email we can use for get_email_data
            email_model_one = EmailService.add_email(subject='My Email Subject',
                                                     sender='sender@example.com',
                                                     recipients=['joe@example.com'],
                                                     name='My Email Name',
                                                     content='asdf',
                                                     content_html=None,
                                                     study_id=study.id,
                                                     workflow_spec_id=email_workflow_spec_id)
            email_model_two = EmailService.add_email(subject='My Other Email Subject',
                                                     sender='sender2@example.com',
                                                     recipients=['joanne@example.com'],
                                                     name='My Email Name',
                                                     content='xyzpdq',
                                                     content_html=None,
                                                     study_id=study.id,
                                                     workflow_spec_id=email_workflow_spec_id)

            workflow_api = self.get_workflow_api(workflow)
            task = workflow_api.next_task

            # Run workflow with get_email_data
            workflow_api = self.complete_form(workflow, task, {'workflow_spec_id': email_workflow_spec_id})
            task = workflow_api.next_task
            data = task.data

            # Make assertions
            self.assertIn('email_data', data)
            email_data = data['email_data']
            self.assertEqual(2, len(email_data))
            self.assertIn('doc_codes', email_data[0])
            self.assertEqual('My Email Subject', email_data[0]['subject'])
            self.assertEqual('sender@example.com', email_data[0]['sender'])
            self.assertEqual('[\'joe@example.com\']', email_data[0]['recipients'])
            self.assertEqual('My Email Name', email_data[0]['name'])

            self.assertIn('doc_codes', email_data[1])
            self.assertEqual('My Other Email Subject', email_data[1]['subject'])
            self.assertEqual('sender2@example.com', email_data[1]['sender'])
            self.assertEqual('[\'joanne@example.com\']', email_data[1]['recipients'])
            self.assertEqual('My Email Name', email_data[1]['name'])

    def test_get_email_data_with_attachments(self):
        self.create_reference_document()
        irb_code_1 = 'Study_App_Doc'
        irb_code_2 = 'Study_Protocol_Document'

        workflow = self.create_workflow('get_email_data')
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
        attachment_files = [
            {'id': 1, 'name': 'something.png', 'type': 'image/png', 'data': b'1234', 'doc_code': 'Study_App_Doc'},
            {'id': 2, 'name': 'another.png', 'type': 'image/png', 'data': b'67890', 'doc_code': 'Study_App_Doc'},
            {'id': 3, 'name': 'anything.png', 'type': 'image/png', 'data': b'5678', 'doc_code': 'Study_Protocol_Document'}
        ]

        with mail.record_messages() as outbox:
            # Send an email we can use for get_email_data
            email_model_one = EmailService.add_email(subject='My Email Subject',
                                                     sender='sender@example.com',
                                                     recipients=['joe@example.com'],
                                                     name='My Email Name',
                                                     content='asdf',
                                                     content_html=None,
                                                     study_id=workflow.study_id,
                                                     workflow_spec_id=workflow.workflow_spec_id,
                                                     attachment_files=attachment_files)

            workflow_api = self.get_workflow_api(workflow)
            task = workflow_api.next_task

            # Run workflow with get_email_data
            workflow_api = self.complete_form(workflow, task, {'email_id': email_model_one.id})
            task = workflow_api.next_task
            data = task.data

            self.assertIn('email_data', data)
            email_data = data['email_data']
            self.assertEqual(1, len(email_data))

            email = email_data[0]
            self.assertIn('doc_codes', email)
            doc_codes = email['doc_codes']
            self.assertEqual(2, len(doc_codes))
            self.assertIn('Study_App_Doc', doc_codes)
            self.assertIn('Study_Protocol_Document', doc_codes)
