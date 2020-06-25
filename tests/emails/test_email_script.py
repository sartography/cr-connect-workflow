from tests.base_test import BaseTest

from crc.models.email import EmailModel
from crc.services.file_service import FileService
from crc.scripts.email import Email
from crc.services.workflow_processor import WorkflowProcessor
from crc.api.common import ApiError

from crc import db, mail


class TestEmailScript(BaseTest):

    def test_do_task(self):
        workflow = self.create_workflow('email')

        task_data = {
          'PIComputingID': 'dhf8r',
          'ApprvlApprvr1': 'lb3dp'
        }
        task = self.get_workflow_api(workflow).next_task

        with mail.record_messages() as outbox:

            self.complete_form(workflow, task, task_data)

            self.assertEqual(len(outbox), 1)
            self.assertEqual(outbox[0].subject, 'Camunda Email Subject')

            # PI is present
            self.assertIn(task_data['PIComputingID'], outbox[0].body)
            self.assertIn(task_data['PIComputingID'], outbox[0].html)

            # Approver is present
            self.assertIn(task_data['ApprvlApprvr1'], outbox[0].body)
            self.assertIn(task_data['ApprvlApprvr1'], outbox[0].html)

            db_emails = EmailModel.query.count()
            self.assertEqual(db_emails, 1)
