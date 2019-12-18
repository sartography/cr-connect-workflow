import enum

from flask_marshmallow.sqla import ModelSchema
from marshmallow_enum import EnumField
from sqlalchemy import func

from crc import db


class ProtocolBuilderStatus(enum.Enum):
    out_of_date = "out_of_date"
    in_process = "in_process"
    complete = "complete"
    updating = "updating"


class StudyModel(db.Model):
    __tablename__ = 'study'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    last_updated = db.Column(db.DateTime(timezone=True), default=func.now())
    protocol_builder_status = db.Column(db.Enum(ProtocolBuilderStatus))
    primary_investigator_id = db.Column(db.String)
    sponsor = db.Column(db.String)
    ind_number = db.Column(db.String)


class StudySchema(ModelSchema):
    class Meta:
        model = StudyModel
    protocol_builder_status = EnumField(ProtocolBuilderStatus)


class WorkflowSpecModel(db.Model):
    __tablename__ = 'workflow_spec'
    id = db.Column(db.String, primary_key=True)
    display_name = db.Column(db.String)
    description = db.Column(db.Text)

class WorkflowSpecSchema(ModelSchema):
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
    bpmn_workflow_json = db.Column(db.TEXT)
    status = db.Column(db.Enum(WorkflowStatus))
    study_id = db.Column(db.Integer, db.ForeignKey('study.id'))
    workflow_spec_id = db.Column(db.Integer, db.ForeignKey('workflow_spec.id'))
    messages: db.Column

class WorkflowSchema(ModelSchema):
    class Meta:
        model = WorkflowModel
    status = EnumField(WorkflowStatus)



