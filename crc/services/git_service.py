from crc import app
from crc.models.git_models import GitRepo
from git import Repo, InvalidGitRepositoryError, NoSuchPathError

from datetime import datetime


class GitService(object):

    @staticmethod
    def __get_repo():
        directory = app.config['SYNC_FILE_ROOT']
        repo = None
        try:
            repo = Repo(directory)
        except InvalidGitRepositoryError as ge:
            # Thrown if the given repository appears to have an invalid format.
            # TODO: I believe this means there is no .git directory
            #  So, git init?
            print(ge)
            repo = Repo.init_repo(directory)
        except NoSuchPathError as pe:
            # TODO: clone from remote?
            print(pe)
        except Exception as e:
            print(e)
        return repo

    def _get_repo(self):
        return self.__get_repo()

    def get_repo(self):
        repo = self.__get_repo()
        repo_model = GitRepo().from_repo(repo)
        return repo_model

    def push_to_remote(self, comment):
        if comment is None:
            comment = f"Git commit: {datetime.now()}"
        repo = self.__get_repo()
        # directory = app.config['SYNC_FILE_ROOT']
        # repo = self.get_repo(directory)
        # get list of changed files
        changes = [item.a_path for item in repo.index.diff(None)]
        # get list of untracked files
        untracked_files = repo.untracked_files
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

    def pull_from_remote(self, branch):
        repo = self.__get_repo()
        repo.git.checkout(branch)
        repo.remotes.origin.pull()
        print(repo)
        return repo

    def get_local_status(self):
        repo = self.__get_repo()
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
