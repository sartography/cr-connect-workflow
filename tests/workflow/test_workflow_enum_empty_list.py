from tests.base_test import BaseTest
import json


class TestEmptyEnumList(BaseTest):

    def test_empty_enum_list(self):

        spec_model = self.load_test_spec('enum_empty_list')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        json_data = json.loads(rv.get_data(as_text=True))

        self.assertEqual(json_data[0]['code'], 'invalid enum')
