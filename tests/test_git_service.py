from tests.base_test import BaseTest

from crc import app
from crc.services.git_service import GitService

from unittest.mock import patch, Mock, call


class TestGitService(BaseTest):

    @staticmethod
    def setup_mock_repo(mock_repo):
        mock_repo.return_value.untracked_files = ['a_file.txt', 'b_file.txt']
        diff_1 = Mock(a_path='c_file.txt', change_type='M')
        diff_2 = Mock(a_path='d_file.txt', change_type='M')
        diff_3 = Mock(a_path='e_file.txt', change_type='D')
        mock_repo.return_value.index.diff = Mock(return_value=[diff_1, diff_2, diff_3])
        mock_repo.return_value.active_branch.name = 'my_active_branch'
        mock_repo.return_value.working_dir = 'working_dir_path'

    @patch('crc.services.git_service.Repo')
    def test_get_repo(self, mock_repo):
        # get_repo returns an instance of our GitRepo object,
        # which we build from a GitPython Repo object.
        # We pass our GitRepo object to a marshmallow schema

        self.setup_mock_repo(mock_repo)
        repo = GitService().get_repo()

        self.assertEqual(repo.modified, ['c_file.txt', 'd_file.txt'])
        self.assertEqual(repo.deleted, ['e_file.txt'])
        self.assertEqual(repo.untracked, ['a_file.txt', 'b_file.txt'])
        self.assertEqual(repo.branch, 'my_active_branch')
        self.assertEqual(repo.directory, 'working_dir_path')

    @patch('crc.services.git_service.Repo')
    def test__get_repo(self, mock_repo):
        # _get_repo returns a GitPython Repo object

        app.config['GIT_DISPLAY_PUSH'] = True
        app.config['GIT_DISPLAY_MERGE'] = False

        self.setup_mock_repo(mock_repo)
        repo = GitService()._get_repo()

        self.assertEqual(repo.active_branch.name, 'my_active_branch')
        self.assertEqual(repo.working_dir, 'working_dir_path')
        self.assertEqual(repo.untracked_files, ['a_file.txt', 'b_file.txt'])
        self.assertEqual(repo.index.diff(None)[0].a_path, 'c_file.txt')
        self.assertEqual(repo.index.diff(None)[1].a_path, 'd_file.txt')
        self.assertEqual(repo.index.diff(None)[2].a_path, 'e_file.txt')
        self.assertTrue(repo.display_push)
        self.assertFalse(repo.display_merge)

    @patch('crc.services.git_service.Repo')
    def test_push_to_remote(self, mock_repo):

        self.setup_mock_repo(mock_repo)
        mock_repo.remotes.origin.push.return_value = 'some_string'

        repo = GitService().push_to_remote(comment='This is my comment')
        method_calls = repo.method_calls
        self.assertIn(call.git.checkout('my_testing_branch'), method_calls)
        self.assertIn(call.index.add(['a_file.txt', 'b_file.txt']), method_calls)
        self.assertIn(call.index.add(['c_file.txt', 'd_file.txt']), method_calls)
        self.assertIn(call.index.remove(['e_file.txt']), method_calls)
        self.assertIn(call.index.commit('This is my comment'), method_calls)
        self.assertIn(call.remotes.origin.push(), method_calls)

    @patch('crc.services.git_service.Repo')
    def test_push_no_comment(self, mock_repo):
        # If no message is passed to push, we generate one.

        self.setup_mock_repo(mock_repo)
        mock_repo.remotes.origin.push.return_value = 'some_string'

        repo = GitService().push_to_remote()
        method_calls = repo.method_calls
        self.assertIn('Git commit:', method_calls[7].args[0])

    @patch('crc.services.git_service.Repo')
    def test_push_empty_comment(self, mock_repo):
        # If no message is passed to push, we generate one.

        self.setup_mock_repo(mock_repo)
        mock_repo.remotes.origin.push.return_value = 'some_string'

        repo = GitService().push_to_remote(comment=' ')
        method_calls = repo.method_calls
        self.assertIn('Git commit:', method_calls[7].args[0])

    def test_get_remote_url(self):
        app.config['GIT_REMOTE_SERVER'] = 'test_server.com'
        app.config['GIT_USER_NAME'] = 'test_username'
        app.config['GIT_USER_PASS'] = 'test_pass'

        result = GitService.get_remote_url('my_test_path')
        self.assertEqual('https://test_username:test_pass@test_server.com/my_test_path.git', result)
