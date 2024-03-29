import json
from tests.base_test import BaseTest


class TestFormFieldType(BaseTest):

    def test_form_field_type(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('workflow_form_field_type')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())

        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(json_data[0]['message'],
                         'Type is missing for field "name". A field type must be provided.')
        # print('TestFormFieldType: Good Form')
