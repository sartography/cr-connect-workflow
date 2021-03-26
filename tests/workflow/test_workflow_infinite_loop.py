from tests.base_test import BaseTest
from crc import app
import json


class TestWorkflowInfiniteLoop(BaseTest):

    def test_workflow_infinite_loop(self):
        self.load_example_data()
        spec_model = self.load_test_spec('infinite_loop')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertIn('There appears to be an infinite loop', json_data[0]['message'])
