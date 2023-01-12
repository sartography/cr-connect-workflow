from tests.base_test import BaseTest
from unittest.mock import patch
from crc import app


class TestGetUserStudies(BaseTest):

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_user_studies(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('user_studies.json')

        workflow = self.create_workflow('get_user_studies')
        user_uid = workflow.study.user_uid

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        form_data = {'user_id': user_uid}
        workflow_api = self.complete_form(workflow, task, form_data)
        task = workflow_api.next_task
        assert task.name == "Event_EndEvent"
        assert "[11111, 54321, 65432, 1]" in task.documentation
