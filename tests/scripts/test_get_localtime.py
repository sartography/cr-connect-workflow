from tests.base_test import BaseTest
from crc.scripts.get_localtime import GetLocaltime
import dateparser


class TestGetLocaltime(BaseTest):

    def test_get_localtime(self):
        self.load_example_data()

        workflow = self.create_workflow('get_localtime')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        timestamp = task.data['timestamp']
        localtime = task.data['localtime']

        self.assertEqual(dateparser.parse(localtime), GetLocaltime().do_task(None, None, None, timestamp=timestamp))
