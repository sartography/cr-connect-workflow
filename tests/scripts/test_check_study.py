from tests.base_test import BaseTest
from crc import app
from unittest.mock import patch


class TestCheckStudy(BaseTest):

    def test_check_study_script_validation(self):
        self.load_example_data()
        spec_model = self.load_test_spec('check_study_script')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)

    @patch('crc.services.protocol_builder.requests.get')
    def test_check_study(self, mock_get):
        app.config['PB_ENABLED'] = True
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('check_study.json')
        workflow = self.create_workflow('check_study_script')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        self.assertIn('DETAIL', task.documentation)
        self.assertIn('STATUS', task.documentation)
