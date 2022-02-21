from tests.base_test import BaseTest


class TestValueExpression(BaseTest):

    # If there is no default value, a value of 'None' should be given.
    def test_no_default(self):

        workflow = self.create_workflow('test_value_expression')

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.complete_form(workflow, first_task, {'value_expression_value': ''})

        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.assertEqual('', second_task.data['value_expression_value'])
        self.assertNotIn('color', second_task.data)


    # If there is dynamic default value, it should be added in to the task data at runtime.
    def test_with_dynamic_default(self):
        workflow = self.create_workflow('test_value_expression')

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.complete_form(workflow, first_task, {'value_expression_value': 'black'})

        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.assertEqual('black', second_task.data['value_expression_value'])
        self.assertEqual('value_expression_value', second_task.form['fields'][0]['default_value'])
        self.assertNotIn('color', second_task.data)
