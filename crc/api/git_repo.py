from crc.models.git_models import GitRepo, GitRepoSchema
from crc.services.git_service import GitService


def get_repo():
    repo_model = GitService().get_repo()
    return GitRepoSchema().dump(repo_model)


def pull_from_remote():
    repo = GitService().pull_from_remote()
    repo_model = GitRepo.from_repo(repo)
    return GitRepoSchema().dump(repo_model)


def push_to_remote(comment=None):
    repo = GitService().push_to_remote(comment)
    repo_model = GitRepo.from_repo(repo)
    return GitRepoSchema().dump(repo_model)


def merge_with_branch(branch):
    repo = GitService().merge_with_branch(branch)
    repo_model = GitRepo.from_repo(repo)
    return GitRepoSchema().dump(repo_model)


# def get_local_status():
#     return GitService().get_local_status()


# def set_repo_branch():
#     pass
#
#
# def commit_repo_changes():
#     pass
