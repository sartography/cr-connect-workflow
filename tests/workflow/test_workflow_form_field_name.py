import json
from tests.base_test import BaseTest


class TestFormFieldName(BaseTest):

    def test_form_field_name(self):
        spec_model = self.load_test_spec('workflow_form_field_name')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())

        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(json_data[0]['message'],
                         'When populating all fields ... \nInvalid Field name: "user-title".  A field ID must begin '
                         'with a letter, and can only contain letters, numbers, and "_"')

    def test_form_field_name_with_period(self):
        workflow = self.create_workflow('workflow_form_field_name')

        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.complete_form(workflow_api, first_task, {})

        workflow_api = self.get_workflow_api(workflow)
        second_task = workflow_api.next_task
        self.assertEqual('me.name', second_task.form['fields'][1]['id'])
