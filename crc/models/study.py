import datetime
import enum
import json

import marshmallow
from marshmallow import INCLUDE, fields
from marshmallow_enum import EnumField
from sqlalchemy import func

from crc import db, ma
from crc.api.common import ApiErrorSchema, ApiError
from crc.models.file import FileModel, SimpleFileSchema, FileSchema
from crc.models.protocol_builder import ProtocolBuilderStatus, ProtocolBuilderStudy
from crc.models.workflow import WorkflowSpecCategoryModel, WorkflowState, WorkflowStatus, WorkflowSpecModel, \
    WorkflowModel
from crc.services.file_service import FileService
from crc.services.user_service import UserService


class StudyStatus(enum.Enum):
    in_progress = 'in_progress'
    hold = 'hold'
    open_for_enrollment = 'open_for_enrollment'
    abandoned = 'abandoned'


class IrbStatus(enum.Enum):
    incomplete_in_protocol_builder = 'incomplete in protocol builder'
    completed_in_protocol_builder = 'completed in protocol builder'
    hsr_assigned = 'hsr number assigned'


class StudyEventType(enum.Enum):
    user = 'user'
    automatic = 'automatic'



class StudyModel(db.Model):
    __tablename__ = 'study'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    last_updated = db.Column(db.DateTime(timezone=True), default=func.now())
    status = db.Column(db.Enum(StudyStatus))
    irb_status = db.Column(db.Enum(IrbStatus))
    primary_investigator_id = db.Column(db.String, nullable=True)
    sponsor = db.Column(db.String, nullable=True)
    hsr_number = db.Column(db.String, nullable=True)
    ind_number = db.Column(db.String, nullable=True)
    user_uid = db.Column(db.String, db.ForeignKey('user.uid'), nullable=False)
    investigator_uids = db.Column(db.ARRAY(db.String), nullable=True)
    requirements = db.Column(db.ARRAY(db.Integer), nullable=True)
    on_hold = db.Column(db.Boolean, default=False)
    enrollment_date = db.Column(db.DateTime(timezone=True), nullable=True)
    #events = db.relationship("TaskEventModel")
    events_history = db.relationship("StudyEvent", cascade="all, delete, delete-orphan")

    def update_from_protocol_builder(self, pbs: ProtocolBuilderStudy):
        self.hsr_number = pbs.HSRNUMBER
        self.title = pbs.TITLE
        self.user_uid = pbs.NETBADGEID
        self.last_updated = pbs.DATE_MODIFIED

        self.irb_status = IrbStatus.incomplete_in_protocol_builder


class StudyAssociated(db.Model):
    """
    This model allows us to associate people with a study, and optionally
    give them edit access. This allows us to create a table with PI, D_CH, etc.
    and give access to people other than the study owner.
    Task_Events will still work as they have previously
    """
    __tablename__ = 'study_associated_user'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey(StudyModel.id), nullable=False)
    uid = db.Column(db.String, db.ForeignKey('ldap_model.uid'), nullable=False)
    role = db.Column(db.String, nullable=True)
    send_email = db.Column(db.Boolean, nullable=True)
    access = db.Column(db.Boolean, nullable=True)

class StudyEvent(db.Model):
    __tablename__ = 'study_event'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey(StudyModel.id), nullable=False)
    study = db.relationship(StudyModel, back_populates='events_history')
    create_date = db.Column(db.DateTime(timezone=True), default=func.now())
    status = db.Column(db.Enum(StudyStatus))
    comment = db.Column(db.String, default='')
    event_type = db.Column(db.Enum(StudyEventType))
    user_uid = db.Column(db.String, db.ForeignKey('user.uid'), nullable=True)


class WorkflowMetadata(object):
    def __init__(self, id, name = None, display_name = None, description = None, spec_version = None,
                 category_id  = None, category_display_name  = None, state: WorkflowState  = None,
                 status: WorkflowStatus  = None, total_tasks  = None, completed_tasks  = None,
                 is_review=None,display_order = None):
        self.id = id
        self.name = name
        self.display_name = display_name
        self.description = description
        self.spec_version = spec_version
        self.category_id = category_id
        self.category_display_name = category_display_name
        self.state = state
        self.status = status
        self.total_tasks = total_tasks
        self.completed_tasks = completed_tasks
        self.is_review = is_review
        self.display_order = display_order


    @classmethod
    def from_workflow(cls, workflow: WorkflowModel):
        is_review = FileService.is_workflow_review(workflow.workflow_spec_id)
        instance = cls(
            id=workflow.id,
            name=workflow.workflow_spec.name,
            display_name=workflow.workflow_spec.display_name,
            description=workflow.workflow_spec.description,
            spec_version=workflow.spec_version(),
            category_id=workflow.workflow_spec.category_id,
            category_display_name=workflow.workflow_spec.category.display_name,
            state=WorkflowState.optional,
            status=workflow.status,
            total_tasks=workflow.total_tasks,
            completed_tasks=workflow.completed_tasks,
            is_review=is_review,
            display_order=workflow.workflow_spec.display_order
        )
        return instance


class WorkflowMetadataSchema(ma.Schema):
    state = EnumField(WorkflowState)
    status = EnumField(WorkflowStatus)
    class Meta:
        model = WorkflowMetadata
        additional = ["id", "name", "display_name", "description",
                 "total_tasks", "completed_tasks", "display_order",
                      "category_id", "is_review", "category_display_name"]
        unknown = INCLUDE


class Category(object):
    def __init__(self, model: WorkflowSpecCategoryModel):
        self.id = model.id
        self.name = model.name
        self.display_name = model.display_name
        self.display_order = model.display_order


class CategorySchema(ma.Schema):
    workflows = fields.List(fields.Nested(WorkflowMetadataSchema), dump_only=True)
    class Meta:
        model = Category
        additional = ["id", "name", "display_name", "display_order"]
        unknown = INCLUDE


class Study(object):

    def __init__(self, title, last_updated, primary_investigator_id, user_uid,
                 id=None, status=None, irb_status=None, comment="",
                 sponsor="", hsr_number="", ind_number="", categories=[],
                 files=[], approvals=[], enrollment_date=None, events_history=[],
                 last_activity_user="",last_activity_date =None,create_user_display="", **argsv):
        self.id = id
        self.user_uid = user_uid
        self.create_user_display = create_user_display
        self.last_activity_date = last_activity_date
        self.last_activity_user = last_activity_user
        self.title = title
        self.last_updated = last_updated
        self.status = status
        self.irb_status = irb_status
        self.comment = comment
        self.primary_investigator_id = primary_investigator_id
        self.sponsor = sponsor
        self.hsr_number = hsr_number
        self.ind_number = ind_number
        self.categories = categories
        self.approvals = approvals
        self.warnings = []
        self.files = files
        self.enrollment_date = enrollment_date
        self.events_history = events_history

    @classmethod
    def from_model(cls, study_model: StudyModel):
        if study_model is not None and len(study_model.__dict__.items()) > 0:
            args = dict((k, v) for k, v in study_model.__dict__.items() if not k.startswith('_'))
            args['events_history'] = study_model.events_history  # For some reason this attribute is not picked up
            instance = cls(**args)
            return instance
        else:
            raise ApiError(code='empty_study_model',
                           message='There was a problem retrieving your study. StudyModel is empty.')

    def model_args(self):
        """Arguments that can be passed into the Study Model to update it."""
        self_dict = self.__dict__.copy()
        del self_dict["categories"]
        del self_dict["warnings"]
        return self_dict


class StudyForUpdateSchema(ma.Schema):

    id = fields.Integer(required=False, allow_none=True)
    status = EnumField(StudyStatus, by_value=True)
    hsr_number = fields.String(allow_none=True)
    sponsor = fields.String(allow_none=True)
    ind_number = fields.String(allow_none=True)
    enrollment_date = fields.DateTime(allow_none=True)
    comment = fields.String(allow_none=True)

    class Meta:
        model = Study
        unknown = INCLUDE

    @marshmallow.post_load
    def make_study(self, data, **kwargs):
        """Can load the basic study data for updates to the database, but categories are write only"""
        return Study(**data)


class StudyEventSchema(ma.Schema):

    id = fields.Integer(required=False)
    create_date = fields.DateTime()
    status = EnumField(StudyStatus, by_value=True)
    comment = fields.String(allow_none=True)
    event_type = EnumField(StudyEvent, by_value=True)


class StudySchema(ma.Schema):

    id = fields.Integer(required=False, allow_none=True)
    categories = fields.List(fields.Nested(CategorySchema), dump_only=True)
    warnings = fields.List(fields.Nested(ApiErrorSchema), dump_only=True)
    protocol_builder_status = EnumField(StudyStatus, by_value=True)
    status = EnumField(StudyStatus, by_value=True)
    hsr_number = fields.String(allow_none=True)
    sponsor = fields.String(allow_none=True)
    ind_number = fields.String(allow_none=True)
    files = fields.List(fields.Nested(FileSchema), dump_only=True)
    enrollment_date = fields.Date(allow_none=True)
    events_history = fields.List(fields.Nested('StudyEventSchema'), dump_only=True)

    class Meta:
        model = Study
        additional = ["id", "title", "last_updated", "primary_investigator_id", "user_uid",
                      "sponsor", "ind_number", "files", "enrollment_date",
                      "create_user_display", "last_activity_date","last_activity_user",
                      "events_history"]
        unknown = INCLUDE

    @marshmallow.post_load
    def make_study(self, data, **kwargs):
        """Can load the basic study data for updates to the database, but categories are write only"""
        return Study(**data)

