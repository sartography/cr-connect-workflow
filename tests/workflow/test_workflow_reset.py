from tests.base_test import BaseTest
from crc.scripts.reset_workflow import ResetWorkflow


class TestWorkflowReset(BaseTest):

    def test_workflow_reset(self):
        workflow = self.create_workflow('reset_workflow')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.assertEqual('Task_GetName', first_task.name)

        self.complete_form(workflow, first_task, {'name': 'Mona'})
        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.assertEqual('Task_GetAge', second_task.name)

        ResetWorkflow().do_task(second_task, workflow.study_id, workflow.id, workflow_name='reset_workflow')

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        self.assertEqual('Task_GetName', task.name)
