from tests.base_test import BaseTest
import json


class TestNameErrorHint(BaseTest):

    def test_name_error_hint(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()

        spec_model = self.load_test_spec('script_with_name_error')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertIn('Did you mean one of \'[\'spam\'', json_data[0]['message'])
