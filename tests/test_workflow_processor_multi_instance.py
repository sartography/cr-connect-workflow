import logging
import os
import string
import random
from unittest.mock import patch

from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent

from crc import session, db, app
from crc.api.common import ApiError
from crc.models.api_models import MultiInstanceType
from crc.models.file import FileModel, FileDataModel, CONTENT_TYPES
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowSpecModel, WorkflowStatus, WorkflowModel
from crc.services.file_service import FileService
from crc.services.study_service import StudyService
from crc.services.workflow_service import WorkflowService
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
        processor.bpmn_workflow.do_engine_steps()
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(1, len(next_user_tasks))

        task = next_user_tasks[0]

        self.assertEquals(
            {
                'DC': {'user_id': 'asd3v', 'type_full': 'Department Contact'},
                'IRBC': {'user_id': 'asdf32', 'type_full': 'IRB Coordinator'},
                'PI': {'user_id': 'dhf8r', 'type_full': 'Primary Investigator'}
            },
            task.data['StudyInfo']['investigators'])

        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        self.assertEquals("asd3v", task.data["investigator"]["user_id"])

        self.assertEqual("MutiInstanceTask", task.get_name())
        api_task = WorkflowService.spiff_task_to_api_task(task)
        self.assertEquals(MultiInstanceType.sequential, api_task.mi_type)
        self.assertEquals(3, api_task.mi_count)
        self.assertEquals(1, api_task.mi_index)
        task.update_data({"email":"asd3v@virginia.edu"})
        processor.complete_task(task)
        processor.do_engine_steps()

        task = next_user_tasks[0]
        api_task = WorkflowService.spiff_task_to_api_task(task)
        self.assertEqual("MutiInstanceTask", api_task.name)
        task.update_data({"email":"asdf32@virginia.edu"})
        self.assertEquals(3, api_task.mi_count)
        self.assertEquals(2, api_task.mi_index)
        processor.complete_task(task)
        processor.do_engine_steps()

        task = next_user_tasks[0]
        api_task = WorkflowService.spiff_task_to_api_task(task)
        self.assertEqual("MutiInstanceTask", task.get_name())
        task.update_data({"email":"dhf8r@virginia.edu"})
        self.assertEquals(3, api_task.mi_count)
        self.assertEquals(3, api_task.mi_index)
        processor.complete_task(task)
        processor.do_engine_steps()

        self.assertEquals(
            {
                'DC': {'user_id': 'asd3v', 'type_full': 'Department Contact', 'email': 'asd3v@virginia.edu'},
                'IRBC': {'user_id': 'asdf32', 'type_full': 'IRB Coordinator', "email": "asdf32@virginia.edu"},
                'PI': {'user_id': 'dhf8r', 'type_full': 'Primary Investigator', "email": "dhf8r@virginia.edu"}
            },
            task.data['StudyInfo']['investigators'])

        self.assertEqual(WorkflowStatus.complete, processor.get_status())
