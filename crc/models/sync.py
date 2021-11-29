from crc import db, ma


class SyncSourceModel(db.Model):
    __tablename__ = 'sync_sources'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    url = db.Column(db.String)


class SyncWorkflow(object):

    def __init__(self,
                 index=None,
                 workflow_spec_id=None,
                 date_created=None,
                 md5_hash=None,
                 location=None,
                 name=None,
                 new=None,
                 level_0=None):
        self.index = index
        self.workflow_spec_id = workflow_spec_id
        self.date_created = date_created
        self.md5_hash = md5_hash
        self.location = location
        self.name = name
        self.new = new
        self.level_0 = level_0

    def to_dict(self):
        return {'index': self.index,
                'workflow_spec_id': self.workflow_spec_id,
                'date_created': self.date_created,
                'md5_hash': self.md5_hash,
                'location': self.location,
                'name': self.name,
                'new': self.new,
                'level_0': self.level_0}


class SyncWorkflowSchema(ma.Schema):
    class Meta:
        model = SyncWorkflow
        fields = ["index",
                  "workflow_spec_id",
                  "date_created",
                  "md5_hash",
                  "name",
                  "new"]


class SyncFile(object):

    def __init__(self,
                 filename=None,
                 date_created=None,
                 type=None,
                 primary=None,
                 content_type=None,
                 primary_process_id=None,
                 md5_hash=None,
                 location=None,
                 new=None):
        self.filename = filename
        self.date_created = date_created
        self.type = type
        self.primary = primary
        self.content_type = content_type
        self.primary_process_id = primary_process_id
        self.md5_hash = md5_hash
        self.location = location
        self.new = new


class SyncFileSchema(ma.Schema):
    class Meta:
        model = SyncFile
        fields = ["filename",
                  "date_created",
                  "type",
                  "primary",
                  "content_type",
                  "primary_process_id",
                  "md5_hash",
                  "location",
                  "new"]
