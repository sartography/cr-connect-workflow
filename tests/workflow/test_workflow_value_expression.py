from tests.base_test import BaseTest


class TestValueExpression(BaseTest):

    def test_value_expression_no_default(self):

        workflow = self.create_workflow('test_value_expression')

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.complete_form(workflow, first_task, {'value_expression_value': ''})

        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.assertEqual('', second_task.data['value_expression_value'])
        # self.assertNotIn('color', second_task.data)
        self.assertIn('color', second_task.data)
        self.assertIsNone(second_task.data['color']['value'])



    def test_value_expression_with_default(self):

        workflow = self.create_workflow('test_value_expression')

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.complete_form(workflow, first_task, {'value_expression_value': 'black'})

        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.assertEqual('black', second_task.data['value_expression_value'])
        self.assertIn('color', second_task.data)
        self.assertEqual('black', second_task.data['color']['value'])
