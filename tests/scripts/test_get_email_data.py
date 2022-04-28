from tests.base_test import BaseTest
from crc import mail, session
from crc.models.workflow import WorkflowModel
from crc.services.email_service import EmailService


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
            self.assertEqual('My Email Subject', email_data[0]['subject'])
            self.assertEqual('sender@example.com', email_data[0]['sender'])
            self.assertEqual('[\'joe@example.com\']', email_data[0]['recipients'])
            self.assertEqual('My Email Name', email_data[0]['name'])

            self.assertEqual('My Other Email Subject', email_data[1]['subject'])
            self.assertEqual('sender2@example.com', email_data[1]['sender'])
            self.assertEqual('[\'joanne@example.com\']', email_data[1]['recipients'])
            self.assertEqual('My Email Name', email_data[1]['name'])
