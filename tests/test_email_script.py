from tests.base_test import BaseTest


class TestEmailScript(BaseTest):

    def test_email_script(self):

        workflow = self.create_workflow('email_script')

        # Start the workflow.
        first_task = self.get_workflow_api(workflow).next_task
        # self.assertEqual('Activity_GetData', first_task.name)
        workflow = self.get_workflow_api(workflow)
        # self.complete_form(workflow, first_task, {'email_address': 'mike@sartography.com'})
        # self.complete_form(workflow, first_task, {'email_address': 'kcm4zc'}, user_uid='kcm4zc')
        result = self.complete_form(workflow, first_task, {'email_address': "'kcm4zc'"})
        print(result)
        task = self.get_workflow_api(workflow).next_task
        self.assertEqual(task.name, 'string')
        # self.assertEqual('Activity_HowMany', workflow.next_task.name)
