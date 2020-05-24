import marshmallow
from marshmallow import INCLUDE, fields
from marshmallow_enum import EnumField
from sqlalchemy import func

from crc import db, ma
from crc.api.common import ApiErrorSchema
from crc.models.file import FileModel, SimpleFileSchema
from crc.models.protocol_builder import ProtocolBuilderStatus, ProtocolBuilderStudy
from crc.models.workflow import WorkflowSpecCategoryModel, WorkflowState, WorkflowStatus, WorkflowSpecModel, \
    WorkflowModel


class StudyModel(db.Model):
    __tablename__ = 'study'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    last_updated = db.Column(db.DateTime(timezone=True), default=func.now())
    protocol_builder_status = db.Column(db.Enum(ProtocolBuilderStatus))
    primary_investigator_id = db.Column(db.String, nullable=True)
    sponsor = db.Column(db.String, nullable=True)
    hsr_number = db.Column(db.String, nullable=True)
    ind_number = db.Column(db.String, nullable=True)
    user_uid = db.Column(db.String, db.ForeignKey('user.uid'), nullable=False)
    investigator_uids = db.Column(db.ARRAY(db.String), nullable=True)
    requirements = db.Column(db.ARRAY(db.Integer), nullable=True)
    on_hold = db.Column(db.Boolean, default=False)

    def update_from_protocol_builder(self, pbs: ProtocolBuilderStudy):
        self.hsr_number = pbs.HSRNUMBER
        self.title = pbs.TITLE
        self.user_uid = pbs.NETBADGEID
        self.last_updated = pbs.DATE_MODIFIED
        self.protocol_builder_status = ProtocolBuilderStatus.INCOMPLETE

        if pbs.Q_COMPLETE:
            self.protocol_builder_status = ProtocolBuilderStatus.ACTIVE
        if pbs.HSRNUMBER:
            self.protocol_builder_status = ProtocolBuilderStatus.OPEN
        if self.on_hold:
            self.protocol_builder_status = ProtocolBuilderStatus.HOLD

    def files(self):
        _files = FileModel.query.filter_by(workflow_id=self.workflow[0].id)
        return _files


class WorkflowMetadata(object):
    def __init__(self, id, name, display_name, description, spec_version, category_id, state: WorkflowState, status: WorkflowStatus,
                 total_tasks, completed_tasks, display_order):
        self.id = id
        self.name = name
        self.display_name = display_name
        self.description = description
        self.spec_version = spec_version
        self.category_id = category_id
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
            spec_version=workflow.spec_version,
            category_id=workflow.workflow_spec.category_id,
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
                 "total_tasks", "completed_tasks", "display_order"]
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

    def __init__(self, id, title, last_updated, primary_investigator_id, user_uid,
                 protocol_builder_status=None,
                 sponsor="", hsr_number="", ind_number="", categories=[], **argsv):
        self.id = id
        self.user_uid = user_uid
        self.title = title
        self.last_updated = last_updated
        self.protocol_builder_status = protocol_builder_status
        self.primary_investigator_id = primary_investigator_id
        self.sponsor = sponsor
        self.hsr_number = hsr_number
        self.ind_number = ind_number
        self.categories = categories
        self.warnings = []


    @classmethod
    def from_model(cls, study_model: StudyModel):
        args = {k: v for k, v in study_model.__dict__.items() if not k.startswith('_')}
        instance = cls(**args)
        return instance

    def update_model(self, study_model: StudyModel):
        for k,v in  self.__dict__.items():
            if not k.startswith('_'):
                study_model.__dict__[k] = v

    def model_args(self):
        """Arguments that can be passed into the Study Model to update it."""
        self_dict = self.__dict__.copy()
        del self_dict["categories"]
        del self_dict["warnings"]
        return self_dict


class StudySchema(ma.Schema):

    categories = fields.List(fields.Nested(CategorySchema), dump_only=True)
    warnings = fields.List(fields.Nested(ApiErrorSchema), dump_only=True)
    protocol_builder_status = EnumField(ProtocolBuilderStatus)
    hsr_number = fields.String(allow_none=True)

    class Meta:
        model = Study
        additional = ["id", "title", "last_updated", "primary_investigator_id", "user_uid",
                      "sponsor", "ind_number"]
        unknown = INCLUDE

    @marshmallow.post_load
    def make_study(self, data, **kwargs):
        """Can load the basic study data for updates to the database, but categories are write only"""
        return Study(**data)


class StudyFilesSchema(ma.Schema):

    files = fields.Method('_files')

    class Meta:
        model = Study
        additional = ["id", "title", "last_updated", "primary_investigator_id"]

    def _files(self, obj):
        return [file.name for file in obj.files()]
