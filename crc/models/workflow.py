import enum

import marshmallow
from marshmallow import EXCLUDE
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from crc import db


class WorkflowSpecCategoryModel(db.Model):
    __tablename__ = 'workflow_spec_category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    display_name = db.Column(db.String)
    display_order = db.Column(db.Integer)


class WorkflowSpecCategoryModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = WorkflowSpecCategoryModel
        load_instance = True
        include_relationships = True


class WorkflowSpecModel(db.Model):
    __tablename__ = 'workflow_spec'
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    display_name = db.Column(db.String)
    display_order = db.Column(db.Integer, nullable=True)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('workflow_spec_category.id'), nullable=True)
    category = db.relationship("WorkflowSpecCategoryModel")
    is_master_spec = db.Column(db.Boolean, default=False)


class WorkflowSpecModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = WorkflowSpecModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys
        unknown = EXCLUDE

    category = marshmallow.fields.Nested(WorkflowSpecCategoryModelSchema, dump_only=True)


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


class WorkflowModel(db.Model):
    __tablename__ = 'workflow'
    id = db.Column(db.Integer, primary_key=True)
    bpmn_workflow_json = db.Column(db.JSON)
    status = db.Column(db.Enum(WorkflowStatus))
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'))
    study = db.relationship("StudyModel", backref='workflow')
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'))
    workflow_spec = db.relationship("WorkflowSpecModel")
    spec_version = db.Column(db.String)
    total_tasks = db.Column(db.Integer, default=0)
    completed_tasks = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime)
