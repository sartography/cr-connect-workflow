from tests.base_test import BaseTest

from crc import app, session
from crc.services.protocol_builder import ProtocolBuilderService

from unittest.mock import patch


class TestIRBInfo(BaseTest):

    @patch('crc.services.protocol_builder.requests.get')
    def test_irb_info_script(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('irb_info.json')
        workflow = self.create_workflow('irb_info_script')
        irb_info = ProtocolBuilderService.get_irb_info(workflow.study_id)
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.assertEqual('Task_PrintInfo', first_task.name)
        self.assertEqual(f'IRB Info: {irb_info}', first_task.documentation)
