from tests.base_test import BaseTest

from crc import session


class TestGetWorkflowState(BaseTest):

    def get_workflow_state(self, workflow_spec_id):

        workflow = self.create_workflow('get_workflow_state')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        task_data = {'workflow_spec_id': workflow_spec_id}
        try:
            workflow_api = self.complete_form(workflow, task, task_data)
        except AssertionError:
            raise

        task = workflow_api.next_task

        workflow_state = task.data['workflow_state']
        return workflow_state

    def test_get_workflow_state(self):

        test_state = 'required'
        test_state_message = 'This workflow is required.'
        simple_form = self.create_workflow('simple_form')

        # This runs the get_workflow_state script and returns the result from task data
        workflow_state = self.get_workflow_state('simple_form')

        # At first, we have no state or state_message
        self.assertEqual(None, workflow_state['state'])
        self.assertEqual(None, workflow_state['message'])

        # Set the state and state_message
        simple_form.state = test_state
        simple_form.state_message = test_state_message
        session.add(simple_form)
        session.commit()

        # Get workflow_state again
        workflow_state = self.get_workflow_state('simple_form')

        # Now, it should have a state and state_message
        self.assertEqual(test_state, workflow_state['state'])
        self.assertEqual(test_state_message, workflow_state['message'])

    def test_get_workflow_state_bad_spec_id(self):
        with self.assertRaises(AssertionError) as ae:
            self.get_workflow_state('bad_spec_id')
