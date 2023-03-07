from tests.base_test import BaseTest
import json


class TestMissingFormKey(BaseTest):

    def test_missing_form_key(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('missing_form_key')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        json_data = json.loads(rv.get_data(as_text=True))
        # There is no error, forms without a form key should not error out as the latest
        # camunda properties panel creates forms without a form key.
        self.assertEqual([], json_data)
