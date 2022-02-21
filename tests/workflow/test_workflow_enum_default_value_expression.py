from tests.base_test import BaseTest
import json


class TestWorkflowEnumDefault(BaseTest):

    def test_enum_dynamic_default(self):
        workflow = self.create_workflow('enum_value_expression')

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.assertEqual('Activity_UserInput', first_task.name)

        result = self.complete_form(workflow, first_task, {'user_input': True})
        self.assertIn('user_input', result.next_task.data)
        self.assertEqual(True, result.next_task.data['user_input'])
        self.assertIn('lookup_output', result.next_task.data)
        self.assertEqual('black', result.next_task.data['lookup_output'])

        self.assertEqual('Activity_PickColor', result.next_task.name)
        self.assertEqual('black', result.next_task.data['lookup_output'])

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
        self.assertEqual('white', workflow_api.next_task.data['lookup_output'])

