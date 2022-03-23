from tests.base_test import BaseTest
from crc.services.workflow_service import WorkflowService


class TestUncheckedCheckboxDefault(BaseTest):
    """We want to make sure that we don't get null/None back from a boolean checkbox.
       This really requires a test on the frontend,
       since there's no way in validation to leave a checkbox unchecked"""

    def test_checkbox_not_null(self):
        spec_model = self.load_test_spec('unchecked_boolean_checkbox')
        result = WorkflowService.test_spec(spec_model.id)

        self.assertIn('var_a', result)
        self.assertIn(result['var_a'], [True, False])
