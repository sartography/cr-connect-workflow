import enum

from marshmallow import EXCLUDE
from sqlalchemy import func

from crc import db, ma


class WorkflowSpecCategory(object):
    def __init__(self, id, display_name, display_order, admin):
        self.id = id
        self.display_name = display_name
        self.display_order = display_order
        self.admin = admin


class WorkflowSpecCategorySchema(ma.Schema):
    class Meta:
        model = WorkflowSpecCategory
        fields = ["id", "display_name", "display_order", "admin"]


class WorkflowSpecInfo(object):
    def __init__(self, id, display_name, description, category_name, is_master_spec,
                 standalone, library, primary_file_name, primary_process_id, is_review,
                 libraries):
        self.id = id  # Sting unqiue id
        self.display_name = display_name
        self.description = description
        self.category_name = category_name
        self.is_master_spec = is_master_spec
        self.standalone = standalone
        self.library = library
        self.primary_file_name = primary_file_name
        self.primary_process_id = primary_process_id
        self.is_review = is_review
        self.libraries = libraries
        self.category = None  # This should be set immediately after deserializing, based on location


class WorkflowSpecInfoSchema(ma.Schema):
    class Meta:
        model = WorkflowSpecInfo
        fields = ["id", "display_name", "description", "category_id", "is_master_spec,",
                  "standalone", "library", "primary_file_name", "primary_process_id", "is_review",
                  "libraries"]
        unknown = EXCLUDE


class WorkflowState(enum.Enum):
    hidden = "hidden"
    disabled = "disabled"
    required = "required"
    optional = "optional"

    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

    @staticmethod
    def list():
        return list(map(lambda c: c.value, WorkflowState))


class WorkflowStatus(enum.Enum):
    not_started = "not_started"
    user_input_required = "user_input_required"
    waiting = "waiting"
    complete = "complete"
    erroring = "erroring"


class WorkflowModel(db.Model):
    __tablename__ = 'workflow'
    id = db.Column(db.Integer, primary_key=True)
    bpmn_workflow_json = db.Column(db.JSON)
    status = db.Column(db.Enum(WorkflowStatus))
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'))
    study = db.relationship("StudyModel", backref='workflow')
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'))
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime(timezone=True), server_default=func.now())
    user_id = db.Column(db.String, default=None)
