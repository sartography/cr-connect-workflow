import enum

from marshmallow_enum import EnumField
from marshmallow_sqlalchemy import ModelSchema
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


class StudyModelSchema(ModelSchema):
    class Meta:
        model = StudyModel

    protocol_builder_status = EnumField(ProtocolBuilderStatus)
