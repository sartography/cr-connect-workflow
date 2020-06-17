from unittest.mock import patch

from crc import session
from crc.models.api_models import MultiInstanceType
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowStatus
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService
from tests.base_test import BaseTest


class TestWorkflowProcessorMultiInstance(BaseTest):
    """Tests the Workflow Processor as it deals with a Multi-Instance task"""

    mock_investigator_response = {'PI': {
                    'label': 'Primary Investigator',
                    'display': 'Always',
                    'unique': 'Yes',
                    'user_id': 'dhf8r',
                    'display_name': 'Dan Funk'},
                'SC_I': {
                    'label': 'Study Coordinator I',
                    'display': 'Always',
                    'unique': 'Yes',
                    'user_id': None},
                'DC': {
                    'label': 'Department Contact',
                    'display': 'Optional',
                    'unique': 'Yes',
                    'user_id': 'asd3v',
                    'error': 'Unable to locate a user with id asd3v in LDAP'}}

    def _populate_form_with_random_data(self, task):

        WorkflowService.populate_form_with_random_data(task)

    def get_processor(self, study_model, spec_model):
        workflow_model = StudyService._create_workflow_model(study_model, spec_model)
        return WorkflowProcessor(workflow_model)

    @patch('crc.services.study_service.StudyService.get_investigators')
    def test_create_and_complete_workflow(self, mock_study_service):
        # This depends on getting a list of investigators back from the protocol builder.
        mock_study_service.return_value = self.mock_investigator_response

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

        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        self.assertEqual("dhf8r", task.data["investigator"]["user_id"])

        self.assertEqual("MutiInstanceTask", task.get_name())
        api_task = WorkflowService.spiff_task_to_api_task(task)
        self.assertEqual(MultiInstanceType.sequential, api_task.multi_instance_type)
        self.assertEqual(3, api_task.multi_instance_count)
        self.assertEqual(1, api_task.multi_instance_index)
        task.update_data({"investigator":{"email":"asd3v@virginia.edu"}})
        processor.complete_task(task)
        processor.do_engine_steps()

        task = next_user_tasks[0]
        api_task = WorkflowService.spiff_task_to_api_task(task)
        self.assertEqual("MutiInstanceTask", api_task.name)
        task.update_data({"investigator":{"email":"asdf32@virginia.edu"}})
        self.assertEqual(3, api_task.multi_instance_count)
        self.assertEqual(2, api_task.multi_instance_index)
        processor.complete_task(task)
        processor.do_engine_steps()

        task = next_user_tasks[0]
        api_task = WorkflowService.spiff_task_to_api_task(task)
        self.assertEqual("MutiInstanceTask", task.get_name())
        task.update_data({"investigator":{"email":"dhf8r@virginia.edu"}})
        self.assertEqual(3, api_task.multi_instance_count)
        self.assertEqual(3, api_task.multi_instance_index)
        processor.complete_task(task)
        processor.do_engine_steps()
        task = processor.bpmn_workflow.last_task

        expected = self.mock_investigator_response
        expected['PI']['email'] = "asd3v@virginia.edu"
        expected['SC_I']['email'] = "asdf32@virginia.edu"
        expected['DC']['email'] = "dhf8r@virginia.edu"
        self.assertEqual(expected,
            task.data['StudyInfo']['investigators'])

        self.assertEqual(WorkflowStatus.complete, processor.get_status())

    @patch('crc.services.study_service.StudyService.get_investigators')
    def test_create_and_complete_workflow_parallel(self, mock_study_service):
        """Unlike the test above, the parallel task allows us to complete the items in any order."""

        # This depends on getting a list of investigators back from the protocol builder.
        mock_study_service.return_value = self.mock_investigator_response

        self.load_example_data()
        workflow_spec_model = self.load_test_spec("multi_instance_parallel")
        study = session.query(StudyModel).first()
        processor = self.get_processor(study, workflow_spec_model)
        processor.bpmn_workflow.do_engine_steps()

        # In the Parallel instance, there should be three tasks, all of them in the ready state.
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(3, len(next_user_tasks))

        # We can complete the tasks out of order.
        task = next_user_tasks[2]

        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        self.assertEqual("asd3v", task.data["investigator"]["user_id"])  # The last of the tasks

        api_task = WorkflowService.spiff_task_to_api_task(task)
        self.assertEqual(MultiInstanceType.parallel, api_task.multi_instance_type)
        task.update_data({"investigator":{"email":"dhf8r@virginia.edu"}})
        processor.complete_task(task)
        processor.do_engine_steps()

        task = next_user_tasks[0]
        api_task = WorkflowService.spiff_task_to_api_task(task)
        self.assertEqual("MutiInstanceTask", api_task.name)
        task.update_data({"investigator":{"email":"asd3v@virginia.edu"}})
        processor.complete_task(task)
        processor.do_engine_steps()

        task = next_user_tasks[1]
        api_task = WorkflowService.spiff_task_to_api_task(task)
        self.assertEqual("MutiInstanceTask", task.get_name())
        task.update_data({"investigator":{"email":"asdf32@virginia.edu"}})
        processor.complete_task(task)
        processor.do_engine_steps()

        # Completing the tasks out of order, still provides the correct information.
        expected = self.mock_investigator_response
        expected['PI']['email'] = "asd3v@virginia.edu"
        expected['SC_I']['email'] = "asdf32@virginia.edu"
        expected['DC']['email'] = "dhf8r@virginia.edu"
        self.assertEqual(expected,
            task.data['StudyInfo']['investigators'])

        self.assertEqual(WorkflowStatus.complete, processor.get_status())
