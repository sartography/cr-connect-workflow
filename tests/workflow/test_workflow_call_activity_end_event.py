from tests.base_test import BaseTest


class TestCallActivityEndEvent(BaseTest):

    def test_call_activity_end_event(self):
        workflow = self.create_workflow('call_activity_end_event')
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task

        # The tests looks at Element Documentation
        # The actual end event has 'Main Workflow'
        # The call activity has 'Call Event'

        # Make sure we have the correct end event,
        # and not the end event from the call activity

        # This should fail
        with self.assertRaises(AssertionError):
            self.assertIn('Call Event', first_task.documentation)

        # This should pass
        self.assertIn('Main Workflow', first_task.documentation)
