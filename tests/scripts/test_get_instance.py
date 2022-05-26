from tests.base_test import BaseTest

from crc import app


class TestGetInstance(BaseTest):

    def test_get_instance(self):
        instance_name = app.config['INSTANCE_NAME']
        workflow = self.create_workflow('get_instance')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        data = task.data
        self.assertEqual(instance_name, data['instance'])
