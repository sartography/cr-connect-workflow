from tests.base_test import BaseTest
from crc.api.common import ApiError
from crc.scripts.get_localtime import GetLocaltime
import dateparser
import datetime
from unittest.mock import patch


class TestGetLocaltime(BaseTest):

    def test_get_localtime(self):
        timestamp = datetime.datetime.now(datetime.timezone.utc)
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

        timestamp = datetime.datetime.now(datetime.timezone.utc)
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

    @patch('dateparser.parse')  # mock_timestamp
    def test_get_localtime_bad_timestamp(self, mock_timestamp):
        # If we have a bad timestamp, we want the script to run, but return None
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        mock_timestamp.return_value = None
        workflow = self.create_workflow('get_localtime')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        workflow_api = self.complete_form(workflow, task, {'with_timestamp': True,
                                                           'with_timezone': True,
                                                           'timestamp': str(timestamp),
                                                           'timezone': 'US/Eastern'})
        next_task = workflow_api.next_task
        localtime_with = next_task.data['localtime_with']
        localtime_without = next_task.data['localtime_without']

        self.assertIsNone(localtime_with)
        self.assertIsNone(localtime_without)
