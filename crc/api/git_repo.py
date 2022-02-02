from crc.models.git_models import GitRepoSchema
from crc.services.git_service import GitService


def get_repo():
    repo_model = GitService().get_repo()
    return GitRepoSchema().dump(repo_model)


def pull_from_remote():
    return GitService().pull_from_remote()


def push_to_remote(comment=None):
    repo_model = GitService().push_to_remote(comment)
    return GitRepoSchema().dump(repo_model)


def merge_with_branch(branch):
    repo_model = GitService().merge_with_branch(branch)
    return GitRepoSchema().dump(repo_model)


# def get_local_status():
#     return GitService().get_local_status()


# def set_repo_branch():
#     pass
#
#
# def commit_repo_changes():
#     pass
