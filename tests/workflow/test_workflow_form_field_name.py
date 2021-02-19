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
