from tests.base_test import BaseTest


class TestSpecFromWorkflowID(BaseTest):

    def test_get_spec_from_workflow_id(self):
        workflow = self.create_workflow('spec_from_id')
        workflow_spec_id = workflow.workflow_spec_id
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        workflow_api = self.complete_form(workflow, task, {'spec_id': workflow_spec_id})
        task = workflow_api.next_task

        self.assertEqual('spec_from_id', task.data['spec']['id'])
        self.assertEqual('spec_from_id', task.data['spec']['display_name'])
