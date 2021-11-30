from tests.base_test import BaseTest
from crc import app
import json
from unittest.mock import patch


class TestWorkflowInfiniteLoop(BaseTest):

    @patch('crc.services.protocol_builder.requests.get')
    def test_workflow_infinite_loop(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('investigators.json')
        self.load_example_data()
        spec_model = self.load_test_spec('infinite_loop')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertIn('There appears to be no way to complete this workflow, halting validation.', json_data[0]['message'])
