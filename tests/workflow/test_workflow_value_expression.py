from tests.base_test import BaseTest


class TestValueExpression(BaseTest):

    # If there is no default value, a value of 'None' should be given.
    def test_value_expression_no_default(self):

        workflow = self.create_workflow('test_value_expression')

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.complete_form(workflow, first_task, {'value_expression_value': ''})

        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.assertEqual('', second_task.data['value_expression_value'])
        self.assertNotIn('color', second_task.data)



    def test_value_expression_with_default(self):

        workflow = self.create_workflow('test_value_expression')

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.complete_form(workflow, first_task, {'value_expression_value': 'black'})

        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.assertEqual('black', second_task.data['value_expression_value'])
        self.assertIn('color', second_task.data)
        self.assertEqual('black', second_task.data['color'])

    def test_validate_task_with_both_default_and_expression(self):
        # This actually fails validation.
        # We are testing the error message is correct.
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('default_value_expression')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual('default value and value_expression', rv.json[0]['code'])
        self.assertIn('Task_GetName', rv.json[0]['message'])
