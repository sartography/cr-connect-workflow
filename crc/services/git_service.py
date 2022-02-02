import os

from crc import app
from crc.api.common import ApiError
from crc.models.git_models import GitRepo
from git import Repo, InvalidGitRepositoryError, NoSuchPathError, GitCommandError

from datetime import datetime


class GitService(object):

    @staticmethod
    def __get_repo():
        remote = app.config['GIT_REMOTE']
        git_branch = app.config['GIT_BRANCH']
        directory = app.config['SYNC_FILE_ROOT']
        # repo = None
        try:
            repo = Repo(directory)
        except InvalidGitRepositoryError:
            # Thrown if the given repository appears to have an invalid format.
            # I believe this means there is no .git directory
            if os.listdir(directory):
                # If the directory is not empty, we let them decide how to fix it
                raise ApiError(code='invalid_git_repo',
                               message=f'The directory {directory} is not empty, and is not a valid git repository. Please fix this before continuing.')
            else:
                # If the directory is empty, we clone
                repo = Repo.clone_from(remote, directory)
                repo.git.checkout(git_branch)
        except NoSuchPathError:
            # The directory does not exist, so clone
            repo = Repo.clone_from(remote, directory)
            repo.git.checkout(git_branch)
        except Exception as e:
            raise ApiError(code='unknown_exception',
                           message=f'There was an unknown exception. Original message is: {e}')
            print(e)
            app.logger.error(e)
        return repo

    def _get_repo(self):
        # This returns a Repo object
        return self.__get_repo()

    def get_repo(self):
        # This returns an instance of crc.models.git_models.GitRepo,
        # built from a Repo object
        repo = self._get_repo()
        repo_model = GitRepo().from_repo(repo)
        return repo_model

    def push_to_remote(self, comment=None):
        if comment is None:
            comment = f"Git commit: {datetime.now()}"
        repo = self.__get_repo()
        # get list of changed files
        changes = [item.a_path for item in repo.index.diff(None)]
        # get list of untracked files
        untracked_files = repo.untracked_files

        repo.index.add(changes)
        repo.index.add(untracked_files)
        repo.index.commit(comment)
        repo.remotes.origin.push()

        print(repo)
        return repo

    def merge_with_branch(self, branch):
        # https://stackoverflow.com/questions/36799362/how-do-you-merge-the-master-branch-into-a-feature-branch-with-gitpython#36802900
        repo = self._get_repo()
        current = repo.active_branch
        merge_branch = repo.branches[branch]
        base = repo.merge_base(current, merge_branch)
        repo.index.merge_tree(merge_branch, base=base)
        repo.index.commit('Merge main into feature',
                          parent_commits=(current.commit, merge_branch.commit))
        current.checkout(force=True)
        print('merge_with_branch')

    def pull_from_remote(self):
        branch = app.config['GIT_BRANCH']
        repo = self.__get_repo()
        # repo.git.checkout(branch)
        if not repo.is_dirty():
            try:
                repo.remotes.origin.pull()
            except GitCommandError as ce:
                print(ce)
        else:
            raise ApiError(code='dirty_repo',
                           message='You have modified or untracked files. Please fix this before attempting to pull.')
        print(repo)
        return repo

    def get_local_status(self):
        repo = self._get_repo()
        # get list of changed files
        changes = [item.a_path for item in repo.index.diff(None)]
        # get list of untracked files
        untracked_files = repo.untracked_files
        return [changes, untracked_files]

    @staticmethod
    def init_repo(directory):
        return Repo.init(directory)

    # @staticmethod
    # def compare_with_branch(repo, branch):
    #     diff = repo.git.diff(branch)
    #     return diff
    #
    # @staticmethod
    # def get_branches(repo):
    #     branches = []
    #     refs = repo.remote().refs
    #     for ref in refs:
    #         branches.append(ref)
    #     return branches

    # directory = app.config['SYNC_FILE_ROOT']
    # repo = self.get_repo(directory)

    # branches = self.get_branches(repo)
    # for branch in branches:
    #     if branch != repo.active_branch:
    #         print(f'Branch: {branch}')
    #         diff = repo.git.diff(branch.name)
    #         print('##########')
    #         print('##########')
    #         print('##########')
    #         print(diff)
    #         continue
