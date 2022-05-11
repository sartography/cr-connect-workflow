from tests.base_test import BaseTest
from crc import app
from crc.services.workflow_service import WorkflowService
from flask_bpmn.api.api_error import ApiError
from unittest.mock import patch


class TestValidateEndEvent(BaseTest):

    @patch('crc.services.protocol_builder.requests.get')
    def test_validate_end_event(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('study_details.json')

        error_string = """Jinja Template Error:  expected token 'end of statement block', got '='"""


        spec_model = self.load_test_spec('verify_end_event')
        try:
            WorkflowService.test_spec(spec_model.id)
        except ApiError as e:
            self.assertEqual(error_string, e.message)
            self.assertEqual('template_error', e.code)
            self.assertEqual(8, e.line_number)
            self.assertEqual('{%- if value = 1 -%}', e.error_line)
            self.assertEqual('verify_end_event.bpmn', e.file_name)



