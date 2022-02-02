from crc import app, ma


class GitRepo(object):

    @classmethod
    def from_repo(cls, repo):
        instance = cls()
        instance.directory = repo.working_dir
        instance.branch = repo.active_branch.name
        instance.merge_branch = app.config['GIT_MERGE_BRANCH']
        instance.changes = [item.a_path for item in repo.index.diff(None)]
        instance.untracked = repo.untracked_files

        return instance


class GitRepoSchema(ma.Schema):
    class Meta:
        model = GitRepo
        fields = ["directory", "branch", "merge_branch", "changes", "untracked"]


class GitCommit(object):
    pass


class GitCommitSchema(ma.Schema):
    class Meta:
        model = GitCommit
        fields = ["message", "files"]
