from tests.base_test import BaseTest


class TestWorkflowFormJinjaHelp(BaseTest):

    def test_form_help_with_jinja(self):
        workflow = self.create_workflow('form_with_jinja_help')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        self.assertEqual('help', task.form['fields'][0]['properties'][0]['id'])
        self.assertEqual('Hello Cruel World', task.form['fields'][0]['properties'][0]['value'])
