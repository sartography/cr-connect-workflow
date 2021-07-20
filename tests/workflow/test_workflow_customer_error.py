from tests.base_test import BaseTest
from crc.services.workflow_service import WorkflowService
import json


class TestCustomerError(BaseTest):

    def test_customer_error(self):

        self.load_example_data()
        spec_model = self.load_test_spec('failing_gateway_workflow')

        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertIn('hint', rv.json[0])
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual('Add a Condition Type to your gateway path.', json_data[0]['hint'])

    def test_extension_error(self):
        self.load_example_data()
        spec_model = self.load_test_spec('extension_error')

        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertIn('hint', rv.json[0])
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual("You are overriding the title using an extension and it is causing this error. Look under the "
                         "extensions tab for the task, and check the value you are setting for the property.",
                         json_data[0]['hint'])
