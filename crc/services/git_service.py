import os

from crc import app
from crc.api.common import ApiError
from crc.models.git_models import GitRepo
from git import Repo, InvalidGitRepositoryError, NoSuchPathError, GitCommandError

from datetime import datetime


class GitService(object):

    @staticmethod
    def get_remote_url(remote_path):
        # we use github
        # Note that the 'password' is a token generated by github, not the site password
        username = app.config["GIT_USER_NAME"]
        password = app.config["GIT_USER_PASS"]
        remote_url = f"https://{username}:{password}@github.com/{remote_path}.git"
        return remote_url

    @staticmethod
    def setup_repo(remote_path, directory):
        remote_url = GitService.get_remote_url(remote_path)
        repo = Repo.clone_from(remote_url, directory)
        return repo

    def __get_repo(self):
        remote_path = app.config['GIT_REMOTE_PATH']
        git_branch = app.config['GIT_BRANCH']
        directory = app.config['SYNC_FILE_ROOT']
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
                # The directory is empty, so we setup the repo
                repo = self.setup_repo(remote_path, directory)

        except NoSuchPathError:
            # The directory does not exist, so setup
            repo = self.setup_repo(remote_path, directory)

        except Exception as e:
            print(e)
            app.logger.error(e)
            raise ApiError(code='unknown_exception',
                           message=f'There was an unknown exception. Original message is: {e}')
        try:
            repo.git.checkout(git_branch)
        except GitCommandError:
            # The branch might not exist yet, so we create it and its remote ref
            repo.git.branch(git_branch)
            repo.git.checkout(git_branch)
            repo.remotes.origin.push(refspec='{}:{}'.format(git_branch, f'origin/{git_branch}'))
            repo.remotes.origin.fetch()

        # remote_ref = repo.remotes.origin.refs[f'origin/{git_branch}']
        remote_ref = repo.remotes.origin.refs[f'{git_branch}']
        repo.active_branch.set_tracking_branch(remote_ref)
        return repo

    def _get_repo(self):
        # This returns a gitpython Repo object
        return self.__get_repo()

    def get_repo(self):
        # This returns an instance of crc.models.git_models.GitRepo,
        # built from a gitpython Repo object
        repo = self._get_repo()
        repo_model = GitRepo().from_repo(repo)
        return repo_model

    def push_to_remote(self, comment=None):
        if comment is None:
            comment = f"Git commit: {datetime.now()}"
        repo = self._get_repo()
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

    def pull_from_remote(self):
        repo = self._get_repo()
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

    def merge_with_branch(self, branch):
        # https://stackoverflow.com/questions/36799362/how-do-you-merge-the-master-branch-into-a-feature-branch-with-gitpython#36802900
        repo = self._get_repo()
        repo.remotes.origin.fetch()
        merge_branch = repo.remotes.origin.refs[branch]
        base = repo.merge_base(repo.active_branch, merge_branch)
        repo.index.merge_tree(merge_branch, base=base)
        repo.index.commit(f'Merge {branch} into working branch', parent_commits=(repo.active_branch.commit, merge_branch.commit))
        repo.active_branch.checkout(force=True)
        return repo
