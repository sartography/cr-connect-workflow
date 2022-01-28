from crc import app
from git import Repo, InvalidGitRepositoryError, NoSuchPathError


class GitService(object):

    @staticmethod
    def get_repo(directory):
        repo = None
        try:
            repo = Repo(directory)
        except InvalidGitRepositoryError as ge:
            # Thrown if the given repository appears to have an invalid format.
            # TODO: I believe this means there is no .git directory
            #  So, git init?
            print(ge)
        except NoSuchPathError as pe:
            # TODO: clone from remote?
            print(pe)
        except Exception as e:
            print(e)
        return repo

    def push_to_remote(self, comment):
        directory = app.config['SYNC_FILE_ROOT']
        repo = self.get_repo(directory)
        # get list of changed files
        changes = [item.a_path for item in repo.index.diff(None)]
        # get list of untracked files
        untracked_files = repo.untracked_files
        branches = self.get_branches(repo)
        for branch in branches:
            if branch != repo.active_branch:
                print(f'Branch: {branch}')
                diff = repo.git.diff(branch.name)
                print('##########')
                print('##########')
                print('##########')
                print(diff)
                continue

        repo.index.add(changes)
        repo.index.add(untracked_files)
        # repo.index.commit(comment)
        # repo.remotes.origin.push()

        print(repo)
        return repo

    @staticmethod
    def pull_from_remote(repo, branch):
        repo.git.checkout(branch)
        repo.remotes.origin.pull()
        print(repo)
        return repo

    @staticmethod
    def compare_with_branch(repo, branch):
        diff = repo.git.diff(branch)
        return diff

    @staticmethod
    def get_branches(repo):
        branches = []
        refs = repo.remote().refs
        for ref in refs:
            branches.append(ref)
        return branches
