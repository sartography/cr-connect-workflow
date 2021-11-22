from tests.base_test import BaseTest

from crc import app, session
from crc.api.workflow_sync import get_sync_sources, WorkflowSyncService
from crc.models.workflow import WorkflowSpecModel


def setup_test_environ():
    setup = [['CR_SYNC_SOURCE__0__URL', 'https://my.target.com'],
             ['CR_SYNC_SOURCE__0__NAME', 'source name'],
             ['CR_SYNC_SOURCE__1__URL', 'https://my.target2.com'],
             ['CR_SYNC_SOURCE__1__NAME', 'source2 name']]
    for thing in setup:
        app.config[thing[0]] = thing[1]


class TestWorkflowSyncService(BaseTest):

    def test_sync_sources_from_env(self):
        setup_test_environ()
        parsed = get_sync_sources()
        self.assertEqual([{'URL': 'https://my.target.com', 'NAME': 'source name'},
                          {'URL': 'https://my.target2.com', 'NAME': 'source2 name'}],
                         parsed)

    def test_get_master_list(self):
        # remote = 'https://testing.crconnect.uvadcos.io'
        remote = 'localhost:3000'
        master_list = WorkflowSyncService.get_master_list(remote)

        print(f'test_get_master_list: master_list: {master_list}')

    def test_sync_all_changed_workflows(self):
        pass

    def test_get_changed_workflows(self):
        pass

    def test_sync_changed_files(self):
        pass

    def test_get_changed_files(self):
        self.load_example_data()
        remote = 'localhost:3000'
        workflow_spec_model = session.query(WorkflowSpecModel).first()
        changed_files = WorkflowSyncService.get_changed_files(remote, workflow_spec_model.id, as_df=False)

        print('test_get_changed_files')

    def test_get_all_spec_state(self):
        pass

    def test_get_workflow_spec_files(self):
        self.load_example_data()
        workflow_spec_model = session.query(WorkflowSpecModel).first()
        workflow_spec_files = WorkflowSyncService.get_workflow_spec_files(workflow_spec_model.id)

        print('test_get_workflow_spec_files')
