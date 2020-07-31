import datetime
import enum
import json

import marshmallow
from marshmallow import INCLUDE, fields
from marshmallow_enum import EnumField
from sqlalchemy import func

from crc import db, ma
from crc.api.common import ApiErrorSchema
from crc.models.file import FileModel, SimpleFileSchema, FileSchema
from crc.models.protocol_builder import ProtocolBuilderStatus, ProtocolBuilderStudy
from crc.models.workflow import WorkflowSpecCategoryModel, WorkflowState, WorkflowStatus, WorkflowSpecModel, \
    WorkflowModel


class StudyStatus(enum.Enum):
    in_progress = 'in_progress'
    hold = 'hold'
    open_for_enrollment = 'open_for_enrollment'
    abandoned = 'abandoned'


class IrbStatus(enum.Enum):
    incomplete_in_protocol_builder = 'incomplete in protocol builder'
    completed_in_protocol_builder = 'completed in protocol builder'
    hsr_assigned = 'hsr number assigned'


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

    def update_from_protocol_builder(self, pbs: ProtocolBuilderStudy):
        self.hsr_number = pbs.HSRNUMBER
        self.title = pbs.TITLE
        self.user_uid = pbs.NETBADGEID
        self.last_updated = pbs.DATE_MODIFIED

        self.irb_status = IrbStatus.incomplete_in_protocol_builder
        self.status = StudyStatus.in_progress
        if pbs.HSRNUMBER:
            self.irb_status = IrbStatus.hsr_assigned
            self.status = StudyStatus.open_for_enrollment
        if self.on_hold:
            self.status = StudyStatus.hold


class WorkflowMetadata(object):
    def __init__(self, id, name = None, display_name = None, description = None, spec_version = None,
                 category_id  = None, category_display_name  = None, state: WorkflowState  = None,
                 status: WorkflowStatus  = None, total_tasks  = None, completed_tasks  = None,
                 display_order = None):
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
        self.display_order = display_order


    @classmethod
    def from_workflow(cls, workflow: WorkflowModel):
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
                      "category_id", "category_display_name"]
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
                 id=None, status=None, irb_status=None,
                 sponsor="", hsr_number="", ind_number="", categories=[],
                 files=[], approvals=[], enrollment_date=None, **argsv):
        self.id = id
        self.user_uid = user_uid
        self.title = title
        self.last_updated = last_updated
        self.status = status
        self.irb_status = irb_status
        self.primary_investigator_id = primary_investigator_id
        self.sponsor = sponsor
        self.hsr_number = hsr_number
        self.ind_number = ind_number
        self.categories = categories
        self.approvals = approvals
        self.warnings = []
        self.files = files
        self.enrollment_date = enrollment_date

    @classmethod
    def from_model(cls, study_model: StudyModel):
        id = study_model.id # Just read some value, in case the dict expired, otherwise dict may be empty.
        args = dict((k, v) for k, v in study_model.__dict__.items() if not k.startswith('_'))
        instance = cls(**args)
        return instance

    def update_model(self, study_model: StudyModel):
        """As the case for update was very reduced, it's mostly and specifically
        updating only the study status and generating a history record
        """
        status = StudyStatus(self.status)
        study_model.last_updated = datetime.datetime.now()
        study_model.status = status

        if status == StudyStatus.open_for_enrollment:
            study_model.enrollment_date = self.enrollment_date

        # change = {
        #     'status': ProtocolBuilderStatus(self.protocol_builder_status).value,
        #     'comment': '' if not hasattr(self, 'comment') else self.comment,
        #     'date': str(datetime.datetime.now())
        # }

        # if study_model.changes_history:
        #     changes_history = json.loads(study_model.changes_history)
        #     changes_history.append(change)
        # else:
        #     changes_history = [change]
        # study_model.changes_history = json.dumps(changes_history)


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
    approvals = fields.List(fields.Nested('ApprovalSchema'), dump_only=True)
    enrollment_date = fields.Date(allow_none=True)

    class Meta:
        model = Study
        additional = ["id", "title", "last_updated", "primary_investigator_id", "user_uid",
                      "sponsor", "ind_number", "approvals", "files", "enrollment_date"]
        unknown = INCLUDE

    @marshmallow.post_load
    def make_study(self, data, **kwargs):
        """Can load the basic study data for updates to the database, but categories are write only"""
        return Study(**data)

