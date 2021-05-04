from tests.base_test import BaseTest
import json


class TestWorkflowEnumDefault(BaseTest):

    def test_enum_default_from_value_expression(self):
        workflow = self.create_workflow('enum_value_expression')

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.assertEqual('Activity_UserInput', first_task.name)

        result = self.complete_form(workflow, first_task, {'user_input': True})
        self.assertIn('user_input', result.next_task.data)
        self.assertEqual(True, result.next_task.data['user_input'])
        self.assertIn('lookup_output', result.next_task.data)
        self.assertEqual('black', result.next_task.data['lookup_output'])

        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual('Activity_PickColor', workflow_api.next_task.name)
        self.assertEqual({'value': 'black', 'label': 'Black'}, workflow_api.next_task.data['color_select'])

        #
        workflow = self.create_workflow('enum_value_expression')

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.assertEqual('Activity_UserInput', first_task.name)

        result = self.complete_form(workflow, first_task, {'user_input': False})
        self.assertIn('user_input', result.next_task.data)
        self.assertEqual(False, result.next_task.data['user_input'])
        self.assertIn('lookup_output', result.next_task.data)
        self.assertEqual('white', result.next_task.data['lookup_output'])

        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual('Activity_PickColor', workflow_api.next_task.name)
        self.assertEqual({'value': 'white', 'label': 'White'}, workflow_api.next_task.data['color_select'])

    def test_enum_value_expression_and_default(self):
        spec_model = self.load_test_spec('enum_value_expression_fail')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())

        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(json_data[0]['code'], 'default value and value_expression')
