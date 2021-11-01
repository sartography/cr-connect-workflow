from crc import db, ma
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowModel
from sqlalchemy import func


class TaskLogModel(db.Model):
    __tablename__ = 'task_log'
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String)
    code = db.Column(db.String)
    message = db.Column(db.String)
    study_id = db.Column(db.Integer, db.ForeignKey(StudyModel.id), nullable=False)
    workflow_id = db.Column(db.Integer, db.ForeignKey(WorkflowModel.id), nullable=False)
    task = db.Column(db.String)
    timestamp = db.Column(db.DateTime(timezone=True), default=func.now())


class TaskLogModelSchema(ma.Schema):

    class Meta:
        model = TaskLogModel
        fields = ["id", "level", "code", "message", "study_id", "workflow_id", "timestamp"]
