from tests.base_test import BaseTest
from crc.services.workflow_service import WorkflowService


class TestEvaluateHiddenProperty(BaseTest):

    def test_validate_evaluate_hidden_property_hide(self):
        spec_model = self.load_test_spec('eval_hidden_property_hide')
        result = WorkflowService.test_spec(spec_model.id)
        self.assertEqual(result['field_a'], False)
        self.assertNotIn('field_b', result)
        self.assertNotIn('field_c', result)

    def test_validate_evaluate_hidden_property_display(self):
        spec_model = self.load_test_spec('eval_hidden_property_display')
        result = WorkflowService.test_spec(spec_model.id)
        self.assertEqual(result['field_a'], True)
        self.assertIn(result['field_b'], ['Yes', 'No'])
        self.assertIn(result['field_c'], [True, False])
