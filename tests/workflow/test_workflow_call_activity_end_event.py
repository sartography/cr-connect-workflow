from tests.base_test import BaseTest


class TestCallActivityEndEvent(BaseTest):

    def test_call_activity_end_event(self):
        workflow = self.create_workflow('call_activity_end_event')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        # This test looks at Element Documentation
        # The actual end event has 'Main Workflow'
        # The call activity has 'Call Event'

        # This should fail, but it passes
        self.assertIn('Call Event', first_task.documentation)

        # This should pass, but it fails
        self.assertIn('Main Workflow', first_task.documentation)

        print('call_activity_end_event')