from tests.base_test import BaseTest
from crc.services.protocol_builder import ProtocolBuilderService

from crc import app, session


class TestIRBInfo(BaseTest):

    def test_irb_info_script(self):
        app.config['PB_ENABLED'] = True
        workflow = self.create_workflow('irb_info_script')
        irb_info = ProtocolBuilderService.get_irb_info(workflow.study_id)
        workflow_api = self.get_workflow_api(workflow)
        first_task = workflow_api.next_task
        self.assertEqual('Task_PrintInfo', first_task.name)
        self.assertEqual(f'IRB Info: {irb_info}', first_task.documentation)
