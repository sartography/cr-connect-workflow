import enum

import marshmallow
from ldap3.core.exceptions import LDAPSocketOpenError
from marshmallow import INCLUDE
from sqlalchemy import func

from crc import db, ma
from crc.api.common import ApiError
from crc.models.file import FileDataModel
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowModel
from crc.services.ldap_service import LdapService


class ApprovalStatus(enum.Enum):
    PENDING = "PENDING"   # no one has done jack.
    APPROVED = "APPROVED" # approved by the reviewer
    DECLINED = "DECLINED" # rejected by the reviewer
    CANCELED = "CANCELED" # The document was replaced with a new version and this review is no longer needed.


class ApprovalFile(db.Model):
    file_data_id = db.Column(db.Integer, db.ForeignKey(FileDataModel.id), primary_key=True)
    approval_id = db.Column(db.Integer, db.ForeignKey("approval.id"), primary_key=True)

    approval = db.relationship("ApprovalModel")
    file_data = db.relationship(FileDataModel)


class ApprovalModel(db.Model):
    __tablename__ = 'approval'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey(StudyModel.id), nullable=False)
    study = db.relationship(StudyModel, backref='approval', cascade='all,delete')
    workflow_id = db.Column(db.Integer, db.ForeignKey(WorkflowModel.id), nullable=False)
    workflow = db.relationship(WorkflowModel)
    approver_uid = db.Column(db.String)  # Not linked to user model, as they may not have logged in yet.
    status = db.Column(db.String)
    message = db.Column(db.String, default='')
    date_created = db.Column(db.DateTime(timezone=True), default=func.now())
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
        instance.version = model.version
        instance.title = ''
        if model.study:
            instance.title = model.study.title

        instance.approver = {}
        try:
            ldap_service = LdapService()
            principal_investigator_id = model.study.primary_investigator_id
            user_info = ldap_service.user_info(principal_investigator_id)
        except (ApiError, LDAPSocketOpenError) as exception:
            user_info = None
            instance.approver['display_name'] = 'Primary Investigator details'
            instance.approver['department'] = 'currently not available'

        if user_info:
            # TODO: Rename approver to primary investigator
            instance.approver['uid'] = model.approver_uid
            instance.approver['display_name'] = user_info.display_name
            instance.approver['title'] = user_info.title
            instance.approver['department'] = user_info.department

        instance.associated_files = []
        for approval_file in model.approval_files:
            associated_file = {}
            associated_file['id'] = approval_file.file_data.file_model.id
            associated_file['name'] = approval_file.file_data.file_model.name
            associated_file['content_type'] = approval_file.file_data.file_model.content_type
            instance.associated_files.append(associated_file)

        return instance

    def update_model(self, approval_model: ApprovalModel):
        approval_model.status = self.status
        approval_model.message = self.message


class ApprovalSchema(ma.Schema):
    class Meta:
        model = Approval
        fields = ["id", "study_id", "workflow_id", "version", "title",
            "version", "status", "message", "approver", "associated_files"]
        unknown = INCLUDE

    @marshmallow.post_load
    def make_approval(self, data, **kwargs):
        """Loads the basic approval data for updates to the database"""
        return Approval(**data)

# Carlos:  Here is the data structure I was trying to imagine.
# If I were to continue down my current traing of thought, I'd create
# another class called just "Approval" that can take an ApprovalModel from the
# database and construct a data structure like this one, that can
# be provided to the API at an /approvals endpoint with GET and PUT
# dat = { "approvals": [
#     {"id": 1,
#      "study_id": 20,
#      "workflow_id": 454,
#      "study_title": "Dan Funk (dhf8r)",  # Really it's just the name of the Principal Investigator
#      "workflow_version": "21",
#      "approver": {  # Pulled from ldap
#         "uid": "bgb22",
#         "display_name": "Billy Bob (bgb22)",
#         "title": "E42:He's a hoopy frood",
#         "department": "E0:EN-Eng Study of Parallel Universes",
#      },
#      "files": [
#          {
#              "id": 124,
#              "name": "ResearchRestart.docx",
#              "content_type": "docx-something-whatever"
#          }
#      ]
#      }
#     ...
# ]
