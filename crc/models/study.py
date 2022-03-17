import enum

import marshmallow
from marshmallow import INCLUDE, fields
from marshmallow_enum import EnumField
from sqlalchemy import func

from crc import db, ma
from crc.api.common import ApiErrorSchema, ApiError
from crc.models.file import FileSchema
from crc.models.ldap import LdapModel, LdapSchema
from crc.models.protocol_builder import ProtocolBuilderCreatorStudy
from crc.models.workflow import WorkflowSpecCategory, WorkflowState, WorkflowStatus, WorkflowModel, WorkflowSpecInfo


class StudyStatus(enum.Enum):
    in_progress = 'in_progress'
    hold = 'hold'
    open_for_enrollment = 'open_for_enrollment'
    abandoned = 'abandoned'
    cr_connect_complete = 'cr_connect_complete'


class ProgressStatus(enum.Enum):
    in_progress = 'in_progress'
    submitted_for_pre_review = 'submitted_for_pre_review'
    in_pre_review = 'in_pre_review'
    returned_from_pre_review = 'returned_from_pre_review'
    pre_review_complete = 'pre_review_complete'
    agenda_date_set = 'agenda_date_set'
    approved = 'approved'
    approved_with_conditions = 'approved_with_conditions'
    deferred = 'deferred'
    disapproved = 'disapproved'
    ready_for_pre_review = 'ready_for_pre_review'
    resubmitted_for_pre_review = 'resubmitted_for_pre_review'

class IrbStatus(enum.Enum):
    incomplete_in_protocol_builder = 'incomplete in protocol builder'
    completed_in_protocol_builder = 'completed in protocol builder'


class StudyEventType(enum.Enum):
    user = 'user'
    automatic = 'automatic'


class StudyModel(db.Model):
    __tablename__ = 'study'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    short_title = db.Column(db.String, nullable=True)
    last_updated = db.Column(db.DateTime(timezone=True), server_default=func.now())
    status = db.Column(db.Enum(StudyStatus))
    progress_status = db.Column(db.Enum(ProgressStatus))
    irb_status = db.Column(db.Enum(IrbStatus))
    primary_investigator_id = db.Column(db.String, nullable=True)
    sponsor = db.Column(db.String, nullable=True)
    ind_number = db.Column(db.String, nullable=True)
    user_uid = db.Column(db.String, db.ForeignKey('user.uid'), nullable=False)
    investigator_uids = db.Column(db.ARRAY(db.String), nullable=True)
    requirements = db.Column(db.ARRAY(db.Integer), nullable=True)
    on_hold = db.Column(db.Boolean, default=False)
    enrollment_date = db.Column(db.DateTime(timezone=True), nullable=True)
    #events = db.relationship("TaskEventModel")
    events_history = db.relationship("StudyEvent", cascade="all, delete, delete-orphan")
    short_name = db.Column(db.String, nullable=True)
    proposal_name = db.Column(db.String, nullable=True)

    def update_from_protocol_builder(self, study: ProtocolBuilderCreatorStudy, user_id):
        self.title = study.TITLE
        self.user_uid = user_id
        if study.DATELASTMODIFIED:
            self.last_updated = study.DATELASTMODIFIED
        else:
            self.last_updated = study.DATECREATED

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
    ldap_info = db.relationship(LdapModel)


class StudyAssociatedSchema(ma.Schema):
    class Meta:
        fields=['uid', 'role', 'send_email', 'access', 'ldap_info']
        model = StudyAssociated
        unknown = INCLUDE
    ldap_info = fields.Nested(LdapSchema, dump_only=True)



class StudyEvent(db.Model):
    __tablename__ = 'study_event'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey(StudyModel.id), nullable=False)
    study = db.relationship(StudyModel, back_populates='events_history')
    create_date = db.Column(db.DateTime(timezone=True), server_default=func.now())
    status = db.Column(db.Enum(StudyStatus))
    comment = db.Column(db.String, default='')
    event_type = db.Column(db.Enum(StudyEventType))
    user_uid = db.Column(db.String, db.ForeignKey('user.uid'), nullable=True)


class WorkflowMetadata(object):
    def __init__(self, id, display_name = None, description = None, spec_version = None,
                 category_id  = None, category_display_name  = None, state: WorkflowState  = None,
                 status: WorkflowStatus  = None, total_tasks  = None, completed_tasks  = None,
                 is_review=None,display_order = None, state_message = None, workflow_spec_id=None):
        self.id = id
        self.display_name = display_name
        self.description = description
        self.spec_version = spec_version
        self.category_id = category_id
        self.category_display_name = category_display_name
        self.state = state
        self.state_message = state_message
        self.status = status
        self.total_tasks = total_tasks
        self.completed_tasks = completed_tasks
        self.is_review = is_review
        self.display_order = display_order
        self.workflow_spec_id = workflow_spec_id


    @classmethod
    def from_workflow(cls, workflow: WorkflowModel, spec: WorkflowSpecInfo):
        instance = cls(
            id=workflow.id,
            display_name=spec.display_name,
            description=spec.description,
            category_id=spec.category_id,
            category_display_name=spec.category.display_name,
            state=WorkflowState.optional,
            status=workflow.status,
            total_tasks=workflow.total_tasks,
            completed_tasks=workflow.completed_tasks,
            is_review=spec.is_review,
            display_order=spec.display_order,
            workflow_spec_id=workflow.workflow_spec_id
        )
        return instance


class WorkflowMetadataSchema(ma.Schema):
    state = EnumField(WorkflowState)
    status = EnumField(WorkflowStatus)
    class Meta:
        model = WorkflowMetadata
        additional = ["id", "display_name", "description",
                      "total_tasks", "completed_tasks", "display_order",
                      "category_id", "is_review", "category_display_name", "state_message"]
        unknown = INCLUDE


class Category(object):
    def __init__(self, model: WorkflowSpecCategory):
        self.id = model.id
        self.display_name = model.display_name
        self.display_order = model.display_order
        self.admin = model.admin


class CategorySchema(ma.Schema):
    workflows = fields.List(fields.Nested(WorkflowMetadataSchema), dump_only=True)
    class Meta:
        model = Category
        additional = ["id", "display_name", "display_order", "admin"]
        unknown = INCLUDE


class Study(object):

    def __init__(self, title, short_title, last_updated, primary_investigator_id, user_uid,
                 id=None, status=None, progress_status=None, irb_status=None, short_name=None, proposal_name=None, comment="",
                 sponsor="", ind_number="", categories=[],
                 files=[], approvals=[], enrollment_date=None, events_history=[],
                 last_activity_user="",last_activity_date =None,create_user_display="", **argsv):
        self.id = id
        self.user_uid = user_uid
        self.create_user_display = create_user_display
        self.last_activity_date = last_activity_date
        self.last_activity_user = last_activity_user
        self.title = title
        self.short_title = short_title
        self.last_updated = last_updated
        self.status = status
        self.progress_status = progress_status
        self.irb_status = irb_status
        self.comment = comment
        self.primary_investigator_id = primary_investigator_id
        self.sponsor = sponsor
        self.ind_number = ind_number
        self.categories = categories
        self.approvals = approvals
        self.warnings = []
        self.files = files
        self.enrollment_date = enrollment_date
        self.events_history = events_history
        self.short_name = short_name
        self.proposal_name = proposal_name

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
    progress_status = EnumField(ProgressStatus, by_value=True, allow_none=True)
    short_title = fields.String(allow_none=True)
    sponsor = fields.String(allow_none=True)
    ind_number = fields.String(allow_none=True)
    files = fields.List(fields.Nested(FileSchema), dump_only=True)
    enrollment_date = fields.Date(allow_none=True)
    events_history = fields.List(fields.Nested('StudyEventSchema'), dump_only=True)
    short_name = fields.String(allow_none=True)
    proposal_name = fields.String(allow_none=True)

    class Meta:
        model = Study
        additional = ["id", "title", "short_title", "last_updated", "primary_investigator_id", "user_uid",
                      "sponsor", "ind_number", "files", "enrollment_date",
                      "create_user_display", "last_activity_date", "last_activity_user",
                      "events_history", "short_name", "proposal_name"]
        unknown = INCLUDE

    @marshmallow.post_load
    def make_study(self, data, **kwargs):
        """Can load the basic study data for updates to the database, but categories are write only"""
        return Study(**data)

