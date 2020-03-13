import enum

from marshmallow_sqlalchemy import ModelSchema

from crc import db

class WorkflowSpecCategoryModel(db.Model):
    __tablename__ = 'workflow_spec_category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    display_name = db.Column(db.String)


class WorkflowSpecCategoryModelSchema(ModelSchema):
    class Meta:
        model = WorkflowSpecCategoryModel


class WorkflowSpecModel(db.Model):
    __tablename__ = 'workflow_spec'
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    display_name = db.Column(db.String)
    description = db.Column(db.Text)
    primary_process_id = db.Column(db.String)
    workflow_spec_category_id = db.Column(db.Integer, db.ForeignKey('workflow_spec_category.id'))
    workflow_spec_category = db.relationship("WorkflowSpecCategoryModel")
    is_status = db.Column(db.Boolean)


class WorkflowSpecModelSchema(ModelSchema):
    class Meta:
        model = WorkflowSpecModel
        include_fk = True  # Includes foreign keys


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

