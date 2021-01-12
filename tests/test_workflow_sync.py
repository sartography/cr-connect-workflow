from unittest.mock import patch

from crc import db
from tests.base_test import BaseTest
from crc.api.workflow_sync import get_all_spec_state, \
                                  get_changed_workflows, \
                                  get_workflow_spec_files, \
                                  get_changed_files, \
                                  get_workflow_specification, \
                                  sync_changed_files
from crc.models.workflow import WorkflowSpecModel
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


    @patch('crc.services.workflow_sync.WorkflowSyncService.get_remote_workflow_spec_files')
    def test_file_differences(self, mock_get):
        self.load_example_data()
        othersys = get_workflow_spec_files('random_fact')
        othersys[1]['date_created'] = str(datetime.now())
        othersys[1]['md5_hash'] = '12345'
        mock_get.return_value = othersys
        response = get_changed_files('localhost:0000','random_fact',as_df=False) #endpoint is not used due to mock
        self.assertIsNotNone(response)
        self.assertEqual(len(response),1)
        self.assertEqual(response[0]['filename'], 'random_fact2.bpmn')
        self.assertEqual(response[0]['location'], 'remote')
        self.assertEqual(response[0]['new'], False)


    @patch('crc.services.workflow_sync.WorkflowSyncService.get_remote_workflow_spec_files')
    def test_file_differences(self, mock_get):
        self.load_example_data()
        othersys = get_workflow_spec_files('random_fact')
        rf2pos = 0
        for pos in range(len(othersys)):
            if othersys[pos]['filename'] == 'random_fact2.bpmn':
                rf2pos = pos
        othersys[rf2pos]['date_created'] = str(datetime.now())
        othersys[rf2pos]['md5_hash'] = '12345'
        mock_get.return_value = othersys
        response = get_changed_files('localhost:0000','random_fact',as_df=False) #endpoint is not used due to mock
        self.assertIsNotNone(response)
        self.assertEqual(len(response),1)
        self.assertEqual(response[0]['filename'], 'random_fact2.bpmn')
        self.assertEqual(response[0]['location'], 'remote')
        self.assertEqual(response[0]['new'], False)

    @patch('crc.services.workflow_sync.WorkflowSyncService.get_remote_file_by_hash')
    @patch('crc.services.workflow_sync.WorkflowSyncService.get_remote_workflow_spec_files')
    @patch('crc.services.workflow_sync.WorkflowSyncService.get_remote_workflow_spec')
    def test_workflow_differences(self, workflow_mock, spec_files_mock, file_data_mock):
        self.load_example_data()
        remote_workflow = get_workflow_specification('random_fact')
        self.assertEqual(remote_workflow['display_name'],'Random Fact')
        remote_workflow['description'] = 'This Workflow came from Remote'
        remote_workflow['display_name'] = 'Remote Workflow'
        workflow_mock.return_value = remote_workflow
        othersys = get_workflow_spec_files('random_fact')
        for pos in range(len(othersys)):
            if othersys[pos]['filename'] == 'random_fact2.bpmn':
                rf2pos = pos
        othersys[rf2pos]['date_created'] = str(datetime.now())
        othersys[rf2pos]['md5_hash'] = '12345'
        spec_files_mock.return_value = othersys
        file_data_mock.return_value = self.workflow_sync_response('random_fact2.bpmn')
        response = sync_changed_files('localhost:0000','random_fact') # endpoint not used due to mock
        self.assertIsNotNone(response)
        self.assertEqual(len(response),1)
        self.assertEqual(response[0], 'random_fact2.bpmn')
        files = FileService.get_spec_data_files('random_fact')
        md5sums = [str(f.md5_hash) for f in files]
        self.assertEqual('21bb6f9e-0af7-0ab2-0fc7-ec0f94787e58' in md5sums, True)
        new_local_workflow = get_workflow_specification('random_fact')
        self.assertEqual(new_local_workflow['display_name'],'Remote Workflow')



    @patch('crc.services.workflow_sync.WorkflowSyncService.get_remote_workflow_spec_files')
    @patch('crc.services.workflow_sync.WorkflowSyncService.get_remote_workflow_spec')
    def test_file_deleted(self, workflow_mock, spec_files_mock):
        self.load_example_data()
        remote_workflow = get_workflow_specification('random_fact')
        workflow_mock.return_value = remote_workflow
        othersys = get_workflow_spec_files('random_fact')
        del(othersys[1])
        spec_files_mock.return_value = othersys
        response = sync_changed_files('localhost:0000','random_fact') # endpoint not used due to mock
        self.assertIsNotNone(response)
        # when we delete a local file, we do not return that it was deleted - just
        # a list of updated files. We may want to change this in the future.
        self.assertEqual(len(response),0)
        files = FileService.get_spec_data_files('random_fact')
        self.assertEqual(len(files),1)

