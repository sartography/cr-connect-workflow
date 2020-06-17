from tests.base_test import BaseTest

from crc.services.file_service import FileService
from crc.scripts.email import Email
from crc.services.workflow_processor import WorkflowProcessor
from crc.api.common import ApiError

from crc import db


class TestEmailScript(BaseTest):

    def test_do_task(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('email')
        processor = WorkflowProcessor(workflow)
        task = processor.next_task()
        # TODO: Replace with proper `complete_form` method from test_tasks
        processor.complete_task(task)
        task = processor.next_task()
        task.data = {
          'PIComputingID': 'dhf8r',
          'ApprvlApprvr1': 'lb3dp',
          'Subject': 'Email Script needs your help'
        }

        script = Email()
        script.do_task(task, 'Subject', 'PIComputingID', 'ApprvlApprvr1')

        # TODO: Add proper assertions
        self.assertTrue(True)
