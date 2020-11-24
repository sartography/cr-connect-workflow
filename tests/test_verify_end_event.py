from tests.base_test import BaseTest
from crc.services.workflow_service import WorkflowService
from crc.api.common import ApiError
from jinja2.exceptions import TemplateSyntaxError


class TestValidateEndEvent(BaseTest):

    def test_validate_end_event(self):

        error_string = """Error processing template for task EndEvent_1qvyxg7: expected token 'end of statement block', got '='"""

        self.load_example_data()
        spec_model = self.load_test_spec('verify_end_event')
        try:
            WorkflowService.test_spec(spec_model.id)
        except ApiError as e:
            self.assertEqual(str(e), error_string)
