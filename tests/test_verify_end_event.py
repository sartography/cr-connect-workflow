from tests.base_test import BaseTest
from crc import app
from crc.services.workflow_service import WorkflowService
from crc.api.common import ApiError
from unittest.mock import patch


class TestValidateEndEvent(BaseTest):

    @patch('crc.services.protocol_builder.requests.get')
    def test_validate_end_event(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('study_details.json')

        error_string = """Error processing template for task EndEvent_1qvyxg7: expected token 'end of statement block', got '='"""

        self.load_example_data()
        spec_model = self.load_test_spec('verify_end_event')
        try:
            WorkflowService.test_spec(spec_model.id)
        except ApiError as e:
            self.assertEqual(str(e), error_string)
