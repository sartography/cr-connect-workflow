import enum

import marshmallow
from marshmallow import INCLUDE, fields
from sqlalchemy import func

from crc import db, ma, app
from crc.api.common import ApiError
from crc.models.file import FileDataModel
from crc.models.ldap import LdapSchema
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowModel
from crc.services.file_service import FileService
from crc.services.ldap_service import LdapService


class ApprovalStatus(enum.Enum):
    PENDING = "PENDING"   # no one has done jack.
    APPROVED = "APPROVED" # approved by the reviewer
    DECLINED = "DECLINED" # rejected by the reviewer
    CANCELED = "CANCELED" # The document was replaced with a new version and this review is no longer needed.

    # Used for overall status only, never set on a task.
    AWAITING = "AWAITING"   # awaiting another approval


class ApprovalFile(db.Model):
    file_data_id = db.Column(db.Integer, db.ForeignKey(FileDataModel.id), primary_key=True)
    approval_id = db.Column(db.Integer, db.ForeignKey("approval.id"), primary_key=True)

    approval = db.relationship("ApprovalModel")
    file_data = db.relationship(FileDataModel)


class ApprovalModel(db.Model):
    __tablename__ = 'approval'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey(StudyModel.id), nullable=False)
    study = db.relationship(StudyModel)
    workflow_id = db.Column(db.Integer, db.ForeignKey(WorkflowModel.id), nullable=False)
    workflow = db.relationship(WorkflowModel)
    approver_uid = db.Column(db.String)  # Not linked to user model, as they may not have logged in yet.
    status = db.Column(db.String)
    message = db.Column(db.String, default='')
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
    date_approved = db.Column(db.DateTime(timezone=True), default=None)
    version = db.Column(db.Integer) # Incremented integer, so 1,2,3 as requests are made.
    approval_files = db.relationship(ApprovalFile, back_populates="approval",
                                     cascade="all, delete, delete-orphan",
                                     order_by=ApprovalFile.file_data_id)


class Approval(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @classmethod
    def from_model(cls, model: ApprovalModel):
        # TODO: Reduce the code by iterating over model's dict keys
        instance = cls()
        instance.id = model.id
        instance.study_id = model.study_id
        instance.workflow_id = model.workflow_id
        instance.version = model.version
        instance.approver_uid = model.approver_uid
        instance.status = model.status
        instance.message = model.message
        instance.date_created = model.date_created
        instance.date_approved = model.date_approved
        instance.version = model.version
        instance.title = ''
        instance.related_approvals = []

        if model.study:
            instance.title = model.study.title
        try:
            instance.approver = LdapService.user_info(model.approver_uid)
            instance.primary_investigator = LdapService.user_info(model.study.primary_investigator_id)
        except ApiError as ae:
            app.logger.error("Ldap lookup failed for approval record %i" % model.id)

        doc_dictionary = FileService.get_doc_dictionary()
        instance.associated_files = []
        for approval_file in model.approval_files:
            try:
                extra_info = doc_dictionary[approval_file.file_data.file_model.irb_doc_code]
            except:
                extra_info = None
            associated_file = {}
            associated_file['id'] = approval_file.file_data.file_model.id
            if extra_info:
                irb_doc_code = approval_file.file_data.file_model.irb_doc_code
                associated_file['name'] = '_'.join((extra_info['category1'],
                                                    approval_file.file_data.file_model.name))
                associated_file['description'] = extra_info['description']
            else:
                associated_file['name'] = approval_file.file_data.file_model.name
                associated_file['description'] = 'No description available'
            associated_file['name'] = '(' +  model.study.primary_investigator_id + ')' + associated_file['name']
            associated_file['content_type'] = approval_file.file_data.file_model.content_type
            instance.associated_files.append(associated_file)

        return instance

    def update_model(self, approval_model: ApprovalModel):
        approval_model.status = self.status
        approval_model.message = self.message


class ApprovalSchema(ma.Schema):

    approver = fields.Nested(LdapSchema, dump_only=True)
    primary_investigator = fields.Nested(LdapSchema, dump_only=True)
    related_approvals = fields.List(fields.Nested('ApprovalSchema', allow_none=True, dump_only=True))

    class Meta:
        model = Approval
        fields = ["id", "study_id", "workflow_id", "version", "title",
                  "status", "message", "approver", "primary_investigator",
                  "associated_files", "date_created", "date_approved",
                  "related_approvals"]
        unknown = INCLUDE

    @marshmallow.post_load
    def make_approval(self, data, **kwargs):
        """Loads the basic approval data for updates to the database"""
        return Approval(**data)


