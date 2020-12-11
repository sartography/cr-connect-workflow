from unittest.mock import patch

from crc import db
from tests.base_test import BaseTest
from crc.api.workflow_sync import get_all_spec_state, get_changed_workflows
from crc.models.workflow import WorkflowSpecModel
import json
from datetime import datetime
from crc.services.file_service import FileService

class TestWorkflowSync(BaseTest):

    @patch('crc.services.workflow_sync.WorkflowSyncService.get_all_remote_workflows')
    def test_get_no_changes(self, mock_get):
        self.load_example_data()
        othersys = get_all_spec_state()
        mock_get.return_value = othersys
        response = get_changed_workflows('localhost:0000') # not actually used due to mock
        self.assertIsNotNone(response)
        self.assertEqual(response,[])


    @patch('crc.services.workflow_sync.WorkflowSyncService.get_all_remote_workflows')
    def test_remote_workflow_change(self, mock_get):
        self.load_example_data()
        othersys = get_all_spec_state()
        othersys[1]['date_created'] = str(datetime.now())
        othersys[1]['md5_hash'] = '12345'
        mock_get.return_value = othersys
        response = get_changed_workflows('localhost:0000') #endpoint is not used due to mock
        self.assertIsNotNone(response)
        self.assertEqual(len(response),1)
        self.assertEqual(response[0]['workflow_spec_id'], 'random_fact')
        self.assertEqual(response[0]['location'], 'remote')
        self.assertEqual(response[0]['new'], False)



    @patch('crc.services.workflow_sync.WorkflowSyncService.get_all_remote_workflows')
    def test_remote_workflow_has_new(self, mock_get):
        self.load_example_data()
        othersys = get_all_spec_state()
        othersys.append({'workflow_spec_id':'my_new_workflow',
                         'date_created':str(datetime.now()),
                         'md5_hash': '12345'})
        mock_get.return_value = othersys
        response = get_changed_workflows('localhost:0000') #endpoint is not used due to mock
        self.assertIsNotNone(response)
        self.assertEqual(len(response),1)
        self.assertEqual(response[0]['workflow_spec_id'],'my_new_workflow')
        self.assertEqual(response[0]['location'], 'remote')
        self.assertEqual(response[0]['new'], True)


    @patch('crc.services.workflow_sync.WorkflowSyncService.get_all_remote_workflows')
    def test_local_workflow_has_new(self, mock_get):
        self.load_example_data()

        othersys = get_all_spec_state()
        mock_get.return_value = othersys
        wf_spec = WorkflowSpecModel()
        wf_spec.id = 'abcdefg'
        wf_spec.display_name = 'New Workflow - Yum!!'
        wf_spec.name = 'my_new_workflow'
        wf_spec.description = 'yep - its a new workflow'
        wf_spec.category_id = 0
        wf_spec.display_order = 0
        db.session.add(wf_spec)
        db.session.commit()
        FileService.add_workflow_spec_file(wf_spec,'dummyfile.txt','text',b'this is a test')
        # after setting up the test - I realized that this doesn't return anything for
        # a workflow that is new locally - it just returns nothing
        response = get_changed_workflows('localhost:0000') #endpoint is not used due to mock
        self.assertIsNotNone(response)
        self.assertEqual(response,[])
