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
    description = db.Column(db.Text)
    primary_process_id = db.Column(db.String)
    workflow_spec_category_id = db.Column(db.Integer, db.ForeignKey('workflow_spec_category.id'), nullable=True)
    workflow_spec_category = db.relationship("WorkflowSpecCategoryModel")
    is_master_spec = db.Column(db.Boolean, default=False)


class WorkflowSpecModelSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = WorkflowSpecModel
        load_instance = True
        include_relationships = True
        include_fk = True  # Includes foreign keys
        unknown = EXCLUDE

    workflow_spec_category = marshmallow.fields.Nested(WorkflowSpecCategoryModelSchema, dump_only=True)

class WorkflowState(enum.Enum):
    hidden = "hidden"
    disabled = "disabled"
    required = "required"
    optional = "optional"


class WorkflowStatus(enum.Enum):
    new = "new"
    user_input_required = "user_input_required"
    waiting = "waiting"
    complete = "complete"

class WorkflowModel(db.Model):
    __tablename__ = 'workflow'
    id = db.Column(db.Integer, primary_key=True)
    bpmn_workflow_json = db.Column(db.JSON)
    status = db.Column(db.Enum(WorkflowStatus))
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'))
    workflow_spec_id = db.Column(db.String, db.ForeignKey('workflow_spec.id'))
    spec_version = db.Column(db.String)
