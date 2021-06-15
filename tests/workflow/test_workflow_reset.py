from tests.base_test import BaseTest
from crc.scripts.reset_workflow import ResetWorkflow
from crc.api.common import ApiError


class TestWorkflowReset(BaseTest):

    def test_workflow_reset_validation(self):
        self.load_example_data()
        spec_model = self.load_test_spec('reset_workflow')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)

    def test_workflow_reset(self):
        workflow = self.create_workflow('two_user_tasks')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.assertEqual('Task_GetName', first_task.name)

        self.complete_form(workflow, first_task, {'name': 'Mona'})
        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.assertEqual('Task_GetAge', second_task.name)

        ResetWorkflow().do_task(second_task, workflow.study_id, workflow.id, workflow_name='two_user_tasks')

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        self.assertEqual('Task_GetName', task.name)

    def test_workflow_reset_missing_name(self):
        workflow = self.create_workflow('two_user_tasks')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        with self.assertRaises(ApiError):
            ResetWorkflow().do_task(first_task, workflow.study_id, workflow.id)

    def test_workflow_reset_bad_name(self):
        workflow = self.create_workflow('two_user_tasks')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        with self.assertRaises(ApiError):
            ResetWorkflow().do_task(first_task, workflow.study_id, workflow.id, workflow_name='bad_workflow_name')
