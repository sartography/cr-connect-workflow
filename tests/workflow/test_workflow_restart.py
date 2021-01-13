from tests.base_test import BaseTest


class TestMessageEvent(BaseTest):

    def test_message_event(self):

        workflow = self.create_workflow('message_event')

        first_task = self.get_workflow_api(workflow).next_task
        self.assertEqual('Activity_GetData', first_task.name)
        workflow_api = self.get_workflow_api(workflow, clear_data=True)
        result = self.complete_form(workflow_api, first_task, {'name': 'asdf'})
        self.assertEqual('asdf', result.next_task.data['name'])
        workflow_api = self.get_workflow_api(workflow_api)
        self.assertNotIn('name', workflow_api.next_task.data)

        print('Nice Test')
