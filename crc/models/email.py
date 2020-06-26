from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from marshmallow import EXCLUDE
from sqlalchemy import func

from crc import db
from crc.models.study import StudyModel


class EmailModel(db.Model):
    __tablename__ = 'email'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String)
    sender = db.Column(db.String)
    recipients = db.Column(db.String)
    content = db.Column(db.String)
    content_html = db.Column(db.String)
    study_id = db.Column(db.Integer, db.ForeignKey(StudyModel.id), nullable=True)
    study = db.relationship(StudyModel)
