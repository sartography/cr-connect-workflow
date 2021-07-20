from tests.base_test import BaseTest


class TestDecisionTableDictionaryOutput(BaseTest):

    def test_decision_table_dictionary_output(self):

        workflow = self.create_workflow('decision_table_dictionary_output')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        result = self.complete_form(workflow, first_task, {'name': 'Mona'})
        self.assertIn('dog', result.next_task.data)
        self.assertEqual('Mona', result.next_task.data['dog']['name'])
        self.assertEqual('Aussie Mix', result.next_task.data['dog']['breed'])
