from tests.base_test import BaseTest


class TestEnumCheckbox(BaseTest):

    def test_enum_checkbox_validation(self):
        spec_model = self.load_test_spec('enum_checkbox')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)

    def test_enum_checkbox(self):
        workflow = self.create_workflow('enum_checkbox')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        data_values = [{'value': 'value_1', 'label': 'value_1'}, {'value': 'value_3', 'label': 'value_3'}]

        self.complete_form(workflow, task, {'some_field': data_values})
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        self.assertIn("{'value': 'value_1', 'label': 'value_1'}", task.documentation)
        self.assertIn("{'value': 'value_3', 'label': 'value_3'}", task.documentation)
