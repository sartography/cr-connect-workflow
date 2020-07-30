from marshmallow import INCLUDE, fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from crc import db, ma
from crc.models.study import StudyModel, StudySchema, WorkflowMetadataSchema, WorkflowMetadata
from crc.models.workflow import WorkflowModel


class TaskEventModel(db.Model):
    __tablename__ = 'task_event'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'), nullable=False)
    user_uid = db.Column(db.String, nullable=False) # In some cases the unique user id may not exist in the db yet.
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=False)
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'))
    spec_version = db.Column(db.String)
    action = db.Column(db.String)
    task_id = db.Column(db.String)
    task_name = db.Column(db.String)
    task_title = db.Column(db.String)
    task_type = db.Column(db.String)
    task_state = db.Column(db.String)
    task_lane = db.Column(db.String)
    form_data = db.Column(db.JSON) # And form data submitted when the task was completed.
    mi_type = db.Column(db.String)
    mi_count = db.Column(db.Integer)
    mi_index = db.Column(db.Integer)
    process_name = db.Column(db.String)
    date = db.Column(db.DateTime)


class TaskEventModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = TaskEventModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys


class TaskEvent(object):
    def __init__(self, model: TaskEventModel, study: StudyModel, workflow: WorkflowMetadata):
        self.id = model.id
        self.study = study
        self.workflow = workflow
        self.user_uid = model.user_uid
        self.action = model.action
        self.task_id = model.task_id
        self.task_title = model.task_title
        self.task_name = model.task_name
        self.task_type = model.task_type
        self.task_state = model.task_state
        self.task_lane = model.task_lane


class TaskEventSchema(ma.Schema):

    study = fields.Nested(StudySchema, dump_only=True)
    workflow = fields.Nested(WorkflowMetadataSchema, dump_only=True)
    class Meta:
        model = TaskEvent
        additional = ["id", "user_uid", "action", "task_id", "task_title",
                      "task_name", "task_type", "task_state", "task_lane"]
        unknown = INCLUDE
