import json
from tests.base_test import BaseTest


class TestFormFieldName(BaseTest):

    def test_prefer_task_data_over_previous_form_submission(self):
        """It is nice to have the previous information show up when having to re-complete a form you filled
        out previously.  However, you don't want to overwrite something if it exists in the task-data already.
         You can demonstrate this by setting the same value with two different forms.  The second of the two
         forms should always start with the data submitted by the first form. No mater how many times we submit and
         go back. """

        workflow = self.create_workflow('prefer_task_data_over_previous_form_submission')

        workflow_api = self.get_workflow_api(workflow)
        task_1 = workflow_api.next_task
        self.assertEqual('pick_letter', task_1.name)
        workflow_api = self.complete_form(workflow, task_1, {'template':'a'})
        task_2 = workflow_api.next_task
        self.assertEqual('complete_word', task_2.name)
        self.assertEqual('a', task_2.data['template'])
        workflow_api = self.complete_form(workflow, task_2, {'template':'a'})

        self.restart_workflow_api(workflow_api, clear_data=False)
        workflow_api = self.get_workflow_api(workflow)
        task_1 = workflow_api.next_task
        self.assertEqual('pick_letter', task_1.name)
        workflow_api = self.complete_form(workflow, task_1, {'template':'b'})
        task_2 = workflow_api.next_task
        self.assertEqual('complete_word', task_2.name)
        # HERE is the real test,  if we use the task data, then template is set to "b", but if we
        # overwrite the task_data with the last form submission, it ends up being "a".  If
        # the value is already set in task_data, it should not be overwitten.
        self.assertEqual('b', task_2.data['template'])
