import os

from tests.base_test import BaseTest

from crc import app
from crc.services.git_service import GitService


class TestGitService(BaseTest):

    def test_get_repo(self):
        self.load_example_data()
        cwd = os.getcwd()
        sync_file_root = app.config['SYNC_FILE_ROOT']
        sync_path = os.path.join(cwd, sync_file_root)
        sync_path = os.path.normpath(sync_path)  # removes the dot in sync_path from the join
        # GitService().init_repo(sync_file_root)
        repo = GitService().get_repo()
        # self.assertFalse(repo.bare)
        self.assertEqual(sync_path, repo.directory)

        print('test_get_repo')

    # def test_push_to_remote(self):
    #     result = GitService().push_to_remote()
    #     print(result)
    #
    # def test_pull_from_remote(self):
    #     result = GitService.pull_from_remote()
    #     print(result)
