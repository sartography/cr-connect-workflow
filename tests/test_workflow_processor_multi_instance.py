import logging
import os
import string
import random
from unittest.mock import patch

from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent

from crc import session, db, app
from crc.api.common import ApiError
from crc.models.file import FileModel, FileDataModel, CONTENT_TYPES
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowSpecModel, WorkflowStatus, WorkflowModel
from crc.services.file_service import FileService
from crc.services.study_service import StudyService
from tests.base_test import BaseTest
from crc.services.workflow_processor import WorkflowProcessor


class TestWorkflowProcessorMultiInstance(BaseTest):
    """Tests the Workflow Processor as it deals with a Multi-Instance task"""


    def _populate_form_with_random_data(self, task):
        WorkflowProcessor.populate_form_with_random_data(task)

    def get_processor(self, study_model, spec_model):
        workflow_model = StudyService._create_workflow_model(study_model, spec_model)
        return WorkflowProcessor(workflow_model)

    @patch('crc.services.protocol_builder.requests.get')
    def test_create_and_complete_workflow(self, mock_get):
        # This depends on getting a list of investigators back from the protocol builder.
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('investigators.json')


        self.load_example_data()
        workflow_spec_model = self.load_test_spec("multi_instance")
        study = session.query(StudyModel).first()
        processor = self.get_processor(study, workflow_spec_model)
        self.assertEqual(study.id, processor.bpmn_workflow.data[WorkflowProcessor.STUDY_ID_KEY])
        self.assertIsNotNone(processor)
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(1, len(next_user_tasks))
        task = next_user_tasks[0]
        self.assertEqual("MutiInstanceTask", task.get_name())

        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        self.assertEquals("asd3v", task.data["investigator"]["user_id"])
        task.update_data({"investigator":{"email":"asd3v@virginia.edu"}})
        processor.complete_task(task)


        processor.do_engine_steps()
        self.assertEqual(WorkflowStatus.complete, processor.get_status())
        data = processor.get_data()
        self.assertIsNotNone(data)
        self.assertIn("FactService", data)
