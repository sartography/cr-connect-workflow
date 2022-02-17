from tests.base_test import BaseTest
import json


class TestMissingFormKey(BaseTest):

    def test_missing_form_key(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('missing_form_key')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertIn('code', json_data[0])
        self.assertEqual('missing_form_key', json_data[0]['code'])
