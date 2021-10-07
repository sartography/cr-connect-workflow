from tests.base_test import BaseTest
from crc import mail, session
from crc.models.study import StudyModel
from crc.services.email_service import EmailService


class TestGetEmailData(BaseTest):

    def test_get_email_data(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        with mail.record_messages() as outbox:
            email_model = EmailService.add_email(subject='My Email Subject',
                                                 sender='sender@example.com',
                                                 recipients=['joe@example.com'],
                                                 content='asdf', content_html=None, study_id=study.id)

            workflow = self.create_workflow('get_email_data')
            workflow_api = self.get_workflow_api(workflow)
            task = workflow_api.next_task

            workflow_api = self.complete_form(workflow, task, {'email_id': email_model.id})

            print('test_get_email_data')