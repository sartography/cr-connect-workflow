import enum

from marshmallow import EXCLUDE, post_load, fields
from sqlalchemy import func

from crc import db, ma


class WorkflowSpecCategory(object):
    def __init__(self, id, display_name, display_order, admin):
        self.id = id # A unique string name, lower case, under scores (ie, 'my_category')
        self.display_name = display_name
        self.display_order = display_order
        self.admin = admin
        self.workflows = []

class WorkflowSpecCategorySchema(ma.Schema):
    class Meta:
        model = WorkflowSpecCategory
        fields = ["id", "display_name", "display_order", "admin"]

    @post_load
    def make_cat(self, data, **kwargs):
        return WorkflowSpecCategory(**data)


class WorkflowSpecInfo(object):
    def __init__(self, id, display_name, description,  is_master_spec=False,
                 standalone=False, library=False, primary_file_name='', primary_process_id='',
                 libraries=[], category_id=None, display_order=0, is_review=False):
        self.id = id  # Sting unique id
        self.display_name = display_name
        self.description = description
        self.display_order = display_order
        self.is_master_spec = is_master_spec
        self.standalone = standalone
        self.library = library
        self.primary_file_name = primary_file_name
        self.primary_process_id = primary_process_id
        self.is_review = is_review
        self.libraries = libraries
        self.category_id = category_id

class WorkflowSpecInfoSchema(ma.Schema):
    class Meta:
        model = WorkflowSpecInfo
        fields = ["id", "display_name", "description", "is_master_spec",
                  "standalone", "library", "primary_file_name", "primary_process_id", "is_review",
                  "libraries", "display_order", "is_master_spec", "is_review", "category_id"]
        unknown = EXCLUDE

    @post_load
    def make_spec(self, data, **kwargs):
        return WorkflowSpecInfo(**data)

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
    workflow_spec_id = db.Column(db.String)
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime(timezone=True), server_default=func.now())
    user_id = db.Column(db.String, default=None)
