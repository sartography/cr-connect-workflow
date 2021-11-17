from tests.base_test import BaseTest

from crc import app
from crc.api.workflow_sync import get_sync_sources, WorkflowSyncService


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
