from crc import app, ma


class GitRepo(object):
    # @classmethod
    # def from_models(cls, model: FileModel, data_model, doc_dictionary):
    #     instance = cls()
    #     instance.id = model.id

    @classmethod
    def from_repo(cls, repo):
        instance = cls()
        instance.directory = repo.working_dir
        instance.branch = repo.active_branch
        instance.merge_branch = app.config['GIT_MERGE_BRANCH']
        # instance.user =
        # instance.changes = [item.a_path for item in repo.index.diff(None)]
        # instance.untracked =


class GitCommit(object):
    pass


class GitRepoSchema(ma.Schema):
    class Meta:
        model = GitRepo
        fields = ["directory", "branch"]


class GitCommitSchema(ma.Schema):
    class Meta:
        model = GitCommit
        fields = ["message", "files"]
