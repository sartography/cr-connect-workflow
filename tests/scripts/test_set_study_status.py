from tests.base_test import BaseTest


class TestSetStudyStatus(BaseTest):

    def test_set_study_status_validation(self):
        self.load_example_data()
        spec_model = self.load_test_spec('set_study_status')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)

    def test_set_study_status(self):
        workflow = self.create_workflow('set_study_status')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        original_status = task.data['original_status']
        self.assertEqual('in_progress', original_status)

        workflow_api = self.complete_form(workflow, task, {'selected_status': 'hold'})
        task = workflow_api.next_task

        self.assertEqual('Activity_DisplayStatus', task.name)
        self.assertEqual('hold', task.data['selected_status'])
        self.assertEqual('hold', task.data['new_status'])

    def test_set_study_status_fail(self):

        self.load_example_data()
        workflow = self.create_workflow('set_study_status')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        with self.assertRaises(AssertionError):
            self.complete_form(workflow, task, {'selected_status': 'asdf'})

        print('test_set_study_status_fail')
