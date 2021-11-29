from tests.base_test import BaseTest

from crc import app, session
from crc.api.workflow_sync import get_sync_sources, WorkflowSyncService
from crc.models.file import FileDataModel
from crc.models.sync import SyncFile, SyncWorkflow
from crc.models.workflow import WorkflowSpecModel


def setup_test_environ():
    setup = [['CR_SYNC_SOURCE__0__URL', 'https://my.target.com'],
             ['CR_SYNC_SOURCE__0__NAME', 'source name'],
             ['CR_SYNC_SOURCE__1__URL', 'https://my.target2.com'],
             ['CR_SYNC_SOURCE__1__NAME', 'source2 name']]
    for thing in setup:
        app.config[thing[0]] = thing[1]


class TestWorkflowSyncService(BaseTest):

    remote = 'http://localhost:5000'

    def test_sync_sources_from_env(self):
        setup_test_environ()
        parsed = get_sync_sources()
        self.assertEqual([{'URL': 'https://my.target.com', 'NAME': 'source name'},
                          {'URL': 'https://my.target2.com', 'NAME': 'source2 name'}],
                         parsed)

    def test_get_master_list(self):
        self.load_example_data()
        # setup_test_environ()
        # TODO: Somehow, this needs to be mocked or local
        # remote = 'https://testing.crconnect.uvadcos.io'
        # remote = 'http://localhost:5000'
        master_list = WorkflowSyncService.get_master_list(self.remote)

        print(f'test_get_master_list: master_list: {master_list}')

    def test_sync_all_changed_workflows(self):
        pass

    def test_get_changed_workflows(self):
        changed_workflows = WorkflowSyncService.get_changed_workflows(self.remote,
                                                                      as_df=False,
                                                                      keep_new_local=False)
        self.assertGreater(len(changed_workflows), 0)
        self.assertIsInstance(changed_workflows[0], SyncWorkflow)

    def test_sync_changed_files(self):
        pass

    def test_get_changed_files(self):
        self.load_example_data()
        workflow_spec_model = session.query(WorkflowSpecModel).first()
        changed_files = WorkflowSyncService.get_changed_files(self.remote, workflow_spec_model.id, as_df=False)
        self.assertEqual(1, len(changed_files))
        self.assertIsInstance(changed_files[0], SyncFile)

    def test_get_all_spec_state(self):
        pass

    def test_get_workflow_spec_files(self):
        self.load_example_data()
        workflow_spec_model = session.query(WorkflowSpecModel).first()
        workflow_spec_files = WorkflowSyncService.get_workflow_spec_files(workflow_spec_model.id)
        self.assertEqual(1, len(workflow_spec_files))
        self.assertIsInstance(workflow_spec_files[0], FileDataModel)
