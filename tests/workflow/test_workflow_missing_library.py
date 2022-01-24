from tests.base_test import BaseTest

import json


class TestMissingLibrary(BaseTest):

    def test_missing_library(self):
        """We call a library that does not exist, and
        test to see if our error service hint is in the error message."""
        workflow = self.create_workflow('missing_library')
        url = f'/v1.0/workflow/{workflow.id}?do_engine_steps=True'
        rv = self.app.get(url,
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual('workflow_validation_error', json_data['code'])
        self.assertIn("'Process_Multiply' was not found", json_data['message'])
