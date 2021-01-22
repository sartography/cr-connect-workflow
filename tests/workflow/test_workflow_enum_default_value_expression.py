from tests.base_test import BaseTest


class TestWorkflowEnumDefault(BaseTest):

    def test_enum_default_from_value_expression(self):
        workflow = self.create_workflow('enum_value_expression')

        first_task = self.get_workflow_api(workflow).next_task
        self.assertEqual('Activity_UserInput', first_task.name)
        workflow_api = self.get_workflow_api(workflow)

        result = self.complete_form(workflow_api, first_task, {'user_input': True})
        self.assertIn('user_input', result.next_task.data)
        self.assertEqual(True, result.next_task.data['user_input'])
        self.assertIn('lookup_output', result.next_task.data)
        self.assertEqual('black', result.next_task.data['lookup_output'])

        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual('Activity_PickColor', self.get_workflow_api(workflow_api).next_task.name)
        self.assertEqual({'value': 'black', 'label': 'Black'}, workflow_api.next_task.data['color_select'])

        #
        workflow = self.create_workflow('enum_value_expression')

        first_task = self.get_workflow_api(workflow).next_task
        self.assertEqual('Activity_UserInput', first_task.name)
        workflow_api = self.get_workflow_api(workflow)

        result = self.complete_form(workflow_api, first_task, {'user_input': False})
        self.assertIn('user_input', result.next_task.data)
        self.assertEqual(False, result.next_task.data['user_input'])
        self.assertIn('lookup_output', result.next_task.data)
        self.assertEqual('white', result.next_task.data['lookup_output'])

        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual('Activity_PickColor', self.get_workflow_api(workflow_api).next_task.name)
        self.assertEqual({'value': 'white', 'label': 'White'}, workflow_api.next_task.data['color_select'])
