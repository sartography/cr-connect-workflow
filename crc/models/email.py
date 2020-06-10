from flask_marshmallow.sqla import SQLAlchemyAutoSchema
from marshmallow import EXCLUDE
from sqlalchemy import func

from crc import db
from crc.models.approval import ApprovalModel


class EmailModel(db.Model):
    __tablename__ = 'email'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String)
    sender = db.Column(db.String)
    recipients = db.Column(db.String)
    content = db.Column(db.String)
    content_html = db.Column(db.String)
    approval_id = db.Column(db.Integer, db.ForeignKey(ApprovalModel.id), nullable=False)
    approval = db.relationship(ApprovalModel)
