from unittest.mock import patch

from crc import session
from crc.models.api_models import MultiInstanceType
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowStatus
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService
from tests.base_test import BaseTest


class TestWorkflowProcessorLoopingTask(BaseTest):
    """Tests the Workflow Processor as it deals with a Looping task"""

    def _populate_form_with_random_data(self, task):
        api_task = WorkflowService.spiff_task_to_api_task(task, add_docs_and_forms=True)
        WorkflowService.populate_form_with_random_data(task, api_task, required_only=False)

    def get_processor(self, study_model, spec_model):
        workflow_model = StudyService._create_workflow_model(study_model, spec_model)
        return WorkflowProcessor(workflow_model)

    def test_create_and_complete_workflow(self):
        # This depends on getting a list of investigators back from the protocol builder.

        workflow = self.create_workflow('looping_task')
        task = self.get_workflow_api(workflow).next_task

        self.assertEqual("GetNames", task.name)

        self.assertEqual(task.multi_instance_type, 'looping')
        self.assertEqual(1, task.multi_instance_index)
        self.complete_form(workflow,task,{'GetNames_CurrentVar':{'Name': 'Peter Norvig', 'Nickname': 'Pete'}})
        task = self.get_workflow_api(workflow).next_task

        self.assertEqual(task.multi_instance_type,'looping')
        self.assertEqual(2, task.multi_instance_index)
        self.complete_form(workflow,
                           task,
                           {'GetNames_CurrentVar':{'Name': 'Stuart Russell', 'Nickname': 'Stu'}},
                           terminate_loop=True)

        task = self.get_workflow_api(workflow).next_task
        self.assertEqual(task.name,'Event_End')
        self.assertEqual(workflow.completed_tasks,workflow.total_tasks)
        expectedDict = {
            'GetNames_CurrentVar': 2,
            'GetNames': {
                '1': {'Name': 'Peter Norvig', 'Nickname': 'Pete'},
                '2': {'Name': 'Stuart Russell', 'Nickname': 'Stu'}
            }
        }
        self.assert_dict_contains_subset(task.data, expectedDict)



