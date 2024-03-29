import enum

from marshmallow import INCLUDE, fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from crc import db, ma
from crc.models.study import StudyModel, StudySchema, WorkflowMetadataSchema, WorkflowMetadata
from crc.models.workflow import WorkflowModel
from crc.services.ldap_service import LdapService
from sqlalchemy import func

class TaskAction(enum.Enum):
    COMPLETE = "COMPLETE"
    TOKEN_RESET = "TOKEN_RESET"
    HARD_RESET = "HARD_RESET"
    SOFT_RESET = "SOFT_RESET"
    ASSIGNMENT = "ASSIGNMENT"  # Whenever the lane changes between tasks we assign the task to specific user.


class TaskEventModel(db.Model):
    __tablename__ = 'task_event'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'))
    user_uid = db.Column(db.String, nullable=False) # In some cases the unique user id may not exist in the db yet.
    workflow_id = db.Column(db.Integer, db.ForeignKey('workflow.id'), nullable=False)
    workflow_spec_id = db.Column(db.String)
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
    date = db.Column(db.DateTime(timezone=True),default=func.now())


class TaskEventModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = TaskEventModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys


class TaskEvent(object):
    def __init__(self, model: TaskEventModel, study: StudyModel, workflow: WorkflowModel):
        self.id = model.id
        self.study = study
        # Fixme: this was workflowMetaData - but it is the only place it is used.
        self.workflow = workflow
        self.user_uid = model.user_uid
        self.user_display = LdapService.user_info(model.user_uid).display_name
        self.action = model.action
        self.task_id = model.task_id
        self.task_title = model.task_title
        self.task_name = model.task_name
        self.task_type = model.task_type
        self.task_state = model.task_state
        self.task_lane = model.task_lane
        self.date = model.date


class TaskEventSchema(ma.Schema):

    study = fields.Nested(StudySchema, dump_only=True)
    workflow = fields.Nested(WorkflowMetadataSchema, dump_only=True)
    task_lane = fields.String(allow_none=True, required=False)
    class Meta:
        model = TaskEvent
        additional = ["id", "user_uid", "user_display", "action", "task_id", "task_title",
                      "task_name", "task_type", "task_state", "task_lane", "date"]
        unknown = INCLUDE
