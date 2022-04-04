from crc import app, ma


class GitRepo(object):

    @classmethod
    def from_repo(cls, repo):
        instance = cls()
        instance.directory = repo.working_dir
        instance.branch = repo.active_branch.name
        instance.merge_branch = app.config['GIT_MERGE_BRANCH']
        instance.modified = [item.a_path for item in repo.index.diff(None) if item.change_type == 'M']
        instance.deleted = [item.a_path for item in repo.index.diff(None) if item.change_type == 'D']
        instance.untracked = repo.untracked_files
        instance.display_push = repo.display_push
        instance.display_merge = repo.display_merge

        return instance


class GitRepoSchema(ma.Schema):
    class Meta:
        model = GitRepo
        fields = ["directory", "branch", "merge_branch", "modified", "deleted", "untracked", "display_push", "display_merge"]


class GitCommit(object):
    pass


class GitCommitSchema(ma.Schema):
    class Meta:
        model = GitCommit
        fields = ["message", "files"]
