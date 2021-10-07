from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from marshmallow import EXCLUDE, INCLUDE
from sqlalchemy import func

from crc import db, ma
from crc.models.study import StudyModel


class EmailModel(db.Model):
    __tablename__ = 'email'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String)
    sender = db.Column(db.String)
    recipients = db.Column(db.String)
    cc = db.Column(db.String, nullable=True)
    bcc = db.Column(db.String, nullable=True)
    content = db.Column(db.String)
    content_html = db.Column(db.String)
    study_id = db.Column(db.Integer, db.ForeignKey(StudyModel.id), nullable=True)
    timestamp = db.Column(db.DateTime(timezone=True), default=func.now())
    workflow_id = db.Column(db.String, nullable=True)
    study = db.relationship(StudyModel)


class EmailModelSchema(ma.Schema):
    # TODO: clean this us. Do we need load_instance and unknown?
    class Meta:
        model = EmailModel
        load_instance = True
        additional = ["id", "subject", "sender", "recipients", "timestamp"]
        unknown = INCLUDE
