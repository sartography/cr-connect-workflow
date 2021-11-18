from crc import db, ma


class SyncSourceModel(db.Model):
    __tablename__ = 'sync_sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    url = db.Column(db.String)


class SyncWorkflow(object):

    def __init__(self, index=None, workflow_spec_id=None, date_created=None, md5_hash=None, name=None, new=None):
        self.index = index
        self.workflow_spec_id = workflow_spec_id
        self.date_created = date_created
        self.md5_hash = md5_hash
        self.name = name
        self.new = new


class SyncWorkflowSchema(ma.Schema):
    class Meta:
        model = SyncWorkflow
        fields = ["index", "workflow_spec_id", "date_created", "md5_hash", "name", "new"]
