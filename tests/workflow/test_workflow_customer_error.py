from tests.base_test import BaseTest
from crc.services.workflow_service import WorkflowService
import json


class TestCustomerError(BaseTest):

    def test_customer_error(self):
        # workflow = self.create_workflow('failing_workflow')
        # workflow_api = self.get_workflow_api(workflow)
        # first_task = workflow_api.next_task
        self.load_example_data()
        spec_model = self.load_test_spec('failing_gateway_workflow')
        # final_data = WorkflowService.test_spec(spec_model.id)
        #
        # spec_model = self.load_test_spec('failing_gateway_workflow')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        # json_data = json.loads(rv.get_data(as_text=True))
        #
        print('test_customer_error: ')
