import enum

from marshmallow_sqlalchemy import ModelSchema

from crc import db


class WorkflowSpecModel(db.Model):
    __tablename__ = 'workflow_spec'
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    display_name = db.Column(db.String)
    description = db.Column(db.Text)
    primary_process_id = db.Column(db.String)


class WorkflowSpecModelSchema(ModelSchema):
    class Meta:
        model = WorkflowSpecModel


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

