from tests.base_test import BaseTest

from crc import app


class TestGetInstance(BaseTest):

    def test_get_instance(self):
        server_name = app.config['SERVER_NAME']
        workflow = self.create_workflow('get_instance')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        data = task.data
        self.assertEqual(server_name, data['instance'])
