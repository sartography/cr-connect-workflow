from tests.base_test import BaseTest


class TestReadOnlyField(BaseTest):

    def test_read_only(self):

        workflow = self.create_workflow('read_only_field')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        read_only_field = first_task.data['read_only_field']
        self.complete_form(workflow, first_task, {'read_only_field': read_only_field})
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        self.assertEqual('Read only is asdf', task.documentation)