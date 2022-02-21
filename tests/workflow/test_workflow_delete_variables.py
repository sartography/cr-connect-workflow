from tests.base_test import BaseTest


class TestDeleteVariables(BaseTest):

    def test_delete_variables(self):
        """This workflow creates variables 'a', 'b', 'c', 'd', and 'e',
        then deletes them with the delete_variables script.
        We assert that they are no longer in task.data"""
        workflow = self.create_workflow('delete_variables')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        for item in ('a', 'b', 'c', 'd', 'e'):
            self.assertIn(item, task.data)
        workflow_api = self.complete_form(workflow, task, {})
        task = workflow_api.next_task
        for item in ('a', 'b', 'c', 'd', 'e'):
            self.assertNotIn(item, task.data)
