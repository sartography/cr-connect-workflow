import json

from crc.services.file_service import FileService
from crc.services.workflow_processor import WorkflowProcessor
from tests.base_test import BaseTest
from crc.models.workflow import WorkflowStatus
from crc import db
from crc.api.common import ApiError
from crc.models.task_event import TaskEventModel, TaskEventSchema
from crc.services.workflow_service import WorkflowService


class TestFileDatastore(BaseTest):


    def test_file_datastore_workflow(self):
        self.load_example_data()
        self.create_reference_document()
        # we need to create a file with an IRB code
        # for this study
        workflow = self.create_workflow('file_data_store')
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_workflow_file(workflow_id=workflow.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234', irb_doc_code=irb_code)

        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task_data = processor.bpmn_workflow.last_task.data
        self.assertTrue(str(task_data['fileid']) in task_data['fileurl'])
        self.assertEqual(task_data['filename'],'anything.png')
        self.assertEqual(task_data['output'], 'me')
        self.assertEqual(task_data['output2'], 'nope')

