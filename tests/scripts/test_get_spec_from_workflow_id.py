from tests.base_test import BaseTest


class TestSpecFromWorkflowID(BaseTest):

    def test_get_spec_from_workflow_id(self):
        workflow = self.create_workflow('spec_from_workflow_id')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        workflow_api = self.complete_form(workflow, task, {'workflow_id': workflow.id})
        task = workflow_api.next_task
        self.assertEqual('spec_from_workflow_id', task.data['workflow_spec']['id'])
        self.assertEqual('spec_from_workflow_id', task.data['workflow_spec']['display_name'])
