from tests.base_test import BaseTest
import json


class TestWorkflowHiddenRequiredField(BaseTest):

    def test_require_default(self):
        # We have a field that can be hidden and required.
        # Validation should fail if we don't have a default value.
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('hidden_required_field')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())

        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(json_data[0]['code'], 'hidden and required field missing default')
        self.assertIn('task_id', json_data[0])
        self.assertIn('task_name', json_data[0])
        self.assertIn('Field "name" is required but can be hidden', json_data[0]['message'])

    def test_require_default_pass(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('hidden_required_field_pass')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual(0, len(rv.json))

    def test_require_default_pass_expression(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('hidden_required_field_pass_expression')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual(0, len(rv.json))

    def test_default_used(self):
        # If a field is hidden and required, make sure we use the default value

        workflow = self.create_workflow('hidden_required_field')
        workflow_api = self.get_workflow_api(workflow)

        first_task = workflow_api.next_task
        self.assertEqual('Activity_Hello', first_task.name)

        self.complete_form(workflow, first_task, {})
        workflow_api = self.get_workflow_api(workflow)

        second_task = workflow_api.next_task
        self.assertEqual('Activity_HiddenField', second_task.name)
        self.complete_form(workflow, second_task, {})
        workflow_api = self.get_workflow_api(workflow)

        # The color field is hidden and required. Make sure we use the default value
        third_task = workflow_api.next_task
        self.assertEqual('Activity_CheckDefault', third_task.name)
        self.assertEqual('Gray', third_task.data['color'])
