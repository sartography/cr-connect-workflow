from tests.base_test import BaseTest

from crc.services.git_service import GitService

from unittest.mock import patch, Mock, call


class TestGitService(BaseTest):

    @staticmethod
    def setup_mock_repo(mock_repo):
        mock_repo.return_value.untracked_files = ['a_file.txt', 'b_file.txt']
        diff_1 = Mock(a_path='c_file.txt')
        diff_2 = Mock(a_path='d_file.txt')
        mock_repo.return_value.index.diff = Mock(return_value=[diff_1, diff_2])
        mock_repo.return_value.active_branch.name = 'my_active_branch'
        mock_repo.return_value.working_dir = 'working_dir_path'

    @patch('crc.services.git_service.Repo')
    def test_get_repo(self, mock_repo):
        # get_repo returns an instance of our GitRepo object,
        # which we build from a GitPython Repo object.
        # We pass our GitRepo object to a marshmallow schema

        self.setup_mock_repo(mock_repo)
        repo = GitService().get_repo()

        self.assertEqual(repo.changes, ['c_file.txt', 'd_file.txt'])
        self.assertEqual(repo.untracked, ['a_file.txt', 'b_file.txt'])
        self.assertEqual(repo.branch, 'my_active_branch')
        self.assertEqual(repo.directory, 'working_dir_path')

    @patch('crc.services.git_service.Repo')
    def test__get_repo(self, mock_repo):
        # _get_repo returns a GitPython Repo object

        self.setup_mock_repo(mock_repo)
        repo = GitService()._get_repo()

        self.assertEqual(repo.active_branch.name, 'my_active_branch')
        self.assertEqual(repo.working_dir, 'working_dir_path')
        self.assertEqual(repo.untracked_files, ['a_file.txt', 'b_file.txt'])
        self.assertEqual(repo.index.diff(None)[0].a_path, 'c_file.txt')
        self.assertEqual(repo.index.diff(None)[1].a_path, 'd_file.txt')

    @patch('crc.services.git_service.Repo')
    def test_push_to_remote(self, mock_repo):

        self.setup_mock_repo(mock_repo)
        mock_repo.remotes.origin.push.return_value = 'some_string'

        repo = GitService().push_to_remote(comment='This is my comment')
        method_calls = repo.method_calls
        self.assertIn(call.git.checkout('my_testing_branch'), method_calls)
        self.assertIn(call.index.add(['a_file.txt', 'b_file.txt']), method_calls)
        self.assertIn(call.index.add(['c_file.txt', 'd_file.txt']), method_calls)
        self.assertIn(call.index.commit('This is my comment'), method_calls)
        self.assertIn(call.remotes.origin.push(), method_calls)

    # def test_pull_from_remote(self):
    #     result = GitService.pull_from_remote()
    #     print(result)