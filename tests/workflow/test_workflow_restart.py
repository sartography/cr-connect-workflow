from tests.base_test import BaseTest


class TestMessageEvent(BaseTest):

    def test_message_event(self):

        # self.load_example_data()
        workflow = self.create_workflow('message_event')

        first_task = self.get_workflow_api(workflow).next_task
        self.assertEqual('Activity_GetData', first_task.name)
        workflow_api = self.get_workflow_api(workflow)
        result = self.complete_form(workflow_api, first_task, {'formdata': 'asdf'})
        self.assertIn('formdata', result.next_task.data)
        self.assertEqual('asdf', result.next_task.data['formdata'])
        workflow_api = self.get_workflow_api(workflow_api, clear_data=True)
        self.assertNotIn('formdata', workflow_api.next_task.data)

        print('Nice Test')
