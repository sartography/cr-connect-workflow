from tests.base_test import BaseTest

import json


class TestMissingLibrary(BaseTest):

    def test_missing_library(self):
        """This workflow calls a library that does not exist,
        we validate the workflow, and assert that our error service hint is in the error message."""
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        workflow = self.create_workflow('missing_library')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % workflow.workflow_spec_id, headers=self.logged_in_headers())
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual('workflow_validation_error', json_data[0]['code'])
        self.assertIn("'Process_Multiply' was not found", json_data[0]['message'])
        self.assertEqual('The workflow spec could not be parsed. If you are loading a library, check whether the name is correct.', json_data[0]['hint'])
