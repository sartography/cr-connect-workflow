from tests.base_test import BaseTest
from crc.scripts.get_localtime import GetLocaltime
import dateparser
import datetime


class TestGetLocaltime(BaseTest):

    def test_get_localtime(self):
        self.load_example_data()

        timestamp = datetime.datetime.utcnow()
        workflow = self.create_workflow('get_localtime')

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        workflow_api = self.complete_form(workflow, task, {'with_timestamp': True,
                                                           'with_timezone': False,
                                                           'timestamp': str(timestamp)})
        task = workflow_api.next_task

        # The workflow calls get_localtime twice, once with named arguments and once without
        localtime_with = task.data['localtime_with']
        localtime_without = task.data['localtime_without']

        self.assertEqual(dateparser.parse(localtime_with), GetLocaltime().do_task(None, None, None, timestamp=str(timestamp)))
        self.assertEqual(dateparser.parse(localtime_without), GetLocaltime().do_task(None, None, None, str(timestamp)))

    def test_get_localtime_with_timezone(self):
        self.load_example_data()

        timestamp = datetime.datetime.utcnow()
        workflow = self.create_workflow('get_localtime')

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        workflow_api = self.complete_form(workflow, task, {'with_timestamp': True,
                                                           'with_timezone': True,
                                                           'timestamp': str(timestamp),
                                                           'timezone': 'US/Eastern'})
        task = workflow_api.next_task

        # The workflow calls get_localtime twice, once with named arguments and once without
        localtime_with = task.data['localtime_with']
        localtime_without = task.data['localtime_without']

        self.assertEqual(dateparser.parse(localtime_with), GetLocaltime().do_task(None, None, None, timestamp=str(timestamp), timezone='US/Eastern'))
        self.assertEqual(dateparser.parse(localtime_without), GetLocaltime().do_task(None, None, None, str(timestamp), 'US/Eastern'))

    def test_get_localtime_no_timestamp(self):
        workflow = self.create_workflow('get_localtime')

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        with self.assertRaises(AssertionError):
            self.complete_form(workflow, task, {'with_timestamp': False, 'with_timezone': False})
