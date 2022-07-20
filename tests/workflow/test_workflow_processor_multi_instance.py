from unittest.mock import patch
from tests.base_test import BaseTest

from crc import session, db
from crc.models.api_models import MultiInstanceType
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowStatus, WorkflowModel
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService


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
    def test_load_irb_from_db(self, mock_study_service):
        # This depends on getting a list of investigators back from the protocol builder.
        mock_study_service.return_value = self.mock_investigator_response


        workflow_spec_model = self.create_workflow("irb_api_personnel")
        study = session.query(StudyModel).first()
        processor = WorkflowProcessor(workflow_spec_model)
        processor.do_engine_steps()
        task_list = processor.get_ready_user_tasks()
        processor.complete_task(task_list[0])
        processor.do_engine_steps()
        nav_list = processor.bpmn_workflow.get_flat_nav_list()
        processor.save()
        # reload after save
        processor = WorkflowProcessor(workflow_spec_model)
        nav_list2 = processor.bpmn_workflow.get_flat_nav_list()
        self.assertEqual(nav_list,nav_list2)

    @patch('crc.services.study_service.StudyService.get_investigators')
    def test_create_and_complete_workflow(self, mock_study_service):
        # This depends on getting a list of investigators back from the protocol builder.
        mock_study_service.return_value = self.mock_investigator_response

        self.add_studies()
        workflow_spec_model = self.load_test_spec("multi_instance")
        study = session.query(StudyModel).first()
        processor = self.get_processor(study, workflow_spec_model)
        processor.bpmn_workflow.do_engine_steps()
        self.assertEqual(study.id, processor.bpmn_workflow.data[WorkflowProcessor.STUDY_ID_KEY])
        self.assertIsNotNone(processor)
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        processor.bpmn_workflow.do_engine_steps()
        workflow_api = WorkflowService.processor_to_workflow_api(processor)
        self.assertIsNotNone(workflow_api)
        self.assertIsNotNone(workflow_api.next_task)

        # 1st investigator
        api_task = workflow_api.next_task
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        self.assertEqual("dhf8r", api_task.data["investigator"]["user_id"])
        self.assertTrue(api_task.name.startswith("MultiInstanceTask"))
        self.assertEqual(3, api_task.multi_instance_count)
        self.assertEqual(1, api_task.multi_instance_index)

        task = processor.get_current_user_tasks()[0]
        self.assertEqual(task.id, api_task.id)
        task.update_data({"investigator": {"email": "asd3v@virginia.edu"}})
        processor.complete_task(task)
        processor.do_engine_steps()
        workflow_api = WorkflowService.processor_to_workflow_api(processor)

        # 2nd investigator
        api_task = workflow_api.next_task
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        self.assertEqual(None, api_task.data["investigator"]["user_id"])
        self.assertTrue(api_task.name.startswith("MultiInstanceTask"))
        self.assertEqual(3, api_task.multi_instance_count)
        self.assertEqual(2, api_task.multi_instance_index)

        task = processor.get_current_user_tasks()[0]
        self.assertEqual(task.id, api_task.id)
        task.update_data({"investigator": {"email": "asdf32@virginia.edu"}})
        processor.complete_task(task)
        processor.do_engine_steps()
        workflow_api = WorkflowService.processor_to_workflow_api(processor)

        # 3rd investigator
        api_task = workflow_api.next_task
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        self.assertEqual("asd3v", api_task.data["investigator"]["user_id"])
        self.assertTrue(api_task.name.startswith("MultiInstanceTask"))
        self.assertEqual(3, api_task.multi_instance_count)
        self.assertEqual(3, api_task.multi_instance_index)

        task = processor.get_current_user_tasks()[0]
        self.assertEqual(task.id, api_task.id)
        task.update_data({"investigator": {"email": "dhf8r@virginia.edu"}})
        processor.complete_task(task)
        processor.do_engine_steps()
        workflow_api = WorkflowService.processor_to_workflow_api(processor)

        # Last task
        api_task = workflow_api.next_task

        expected = self.mock_investigator_response
        expected['PI']['email'] = "asd3v@virginia.edu"
        expected['SC_I']['email'] = "asdf32@virginia.edu"
        expected['DC']['email'] = "dhf8r@virginia.edu"

        self.assertEqual(expected, api_task.data['StudyInfo']['investigators'])
        self.assertEqual(WorkflowStatus.complete, processor.get_status())

    def refresh_processor(self, processor):
        """Saves the processor, and returns a new one read in from the database"""
        processor.save()
        processor = WorkflowProcessor(processor.workflow_model)
        return processor

    @patch('crc.services.study_service.StudyService.get_investigators')
    def test_create_and_complete_workflow_parallel(self, mock_study_service):
        """Unlike the test above, the parallel task allows us to complete the items in any order."""

        # This depends on getting a list of investigators back from the protocol builder.
        mock_study_service.return_value = self.mock_investigator_response

        self.add_studies()
        workflow_spec_model = self.load_test_spec("multi_instance_parallel")
        study = session.query(StudyModel).first()
        processor = self.get_processor(study, workflow_spec_model)
        processor = self.refresh_processor(processor)
        processor.bpmn_workflow.do_engine_steps()

        # In the Parallel instance, there should be three tasks, all of them in the ready state.
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(3, len(next_user_tasks))
        # There should be six tasks in the navigation: start event, the script task, end event, and three tasks
        # for the three executions of hte multi-instance.
        self.assertEqual(7, len(processor.bpmn_workflow.get_flat_nav_list()))

        # We can complete the tasks out of order.
        task = next_user_tasks[2]

        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        self.assertEqual("asd3v", task.data["investigator"]["user_id"])  # The last of the tasks

        api_task = WorkflowService.spiff_task_to_api_task(task)
        self.assertEqual(MultiInstanceType.parallel, api_task.multi_instance_type)

        # Assure navigation picks up the label of the current element variable.
        nav = WorkflowService.processor_to_workflow_api(processor, task).navigation
        self.assertEqual("Primary Investigator", nav[1].description)

        task.update_data({"investigator": {"email": "dhf8r@virginia.edu"}})
        processor.complete_task(task)
        processor.do_engine_steps()
        self.assertEqual(7, len(processor.bpmn_workflow.get_flat_nav_list()))

        task = next_user_tasks[0]
        api_task = WorkflowService.spiff_task_to_api_task(task)
        self.assertEqual("MultiInstanceTask", api_task.name)
        task.update_data({"investigator":{"email":"asd3v@virginia.edu"}})
        processor.complete_task(task)
        processor.do_engine_steps()
        self.assertEqual(7, len(processor.bpmn_workflow.get_flat_nav_list()))

        task = next_user_tasks[1]
        api_task = WorkflowService.spiff_task_to_api_task(task)
        self.assertEqual("MultiInstanceTask_0", task.get_name())
        task.update_data({"investigator":{"email":"asdf32@virginia.edu"}})
        processor.complete_task(task)
        processor.do_engine_steps()
        self.assertEqual(7, len(processor.bpmn_workflow.get_flat_nav_list()))

        # Completing the tasks out of order, still provides the correct information.
        expected = self.mock_investigator_response
        expected['PI']['email'] = "asd3v@virginia.edu"
        expected['SC_I']['email'] = "asdf32@virginia.edu"
        expected['DC']['email'] = "dhf8r@virginia.edu"
        self.assertEqual(expected,
            task.data['StudyInfo']['investigators'])

        self.assertEqual(WorkflowStatus.complete, processor.get_status())
        self.assertEqual(7, len(processor.bpmn_workflow.get_flat_nav_list()))
