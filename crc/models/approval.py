import enum

from marshmallow import INCLUDE

from crc import db, ma
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowModel


class ApprovalStatus(enum.Enum):
    WAITING = "WAITING"   # no one has done jack.
    APPROVED = "APPROVED" # approved by the reviewer
    DECLINED = "DECLINED" # rejected by the reviewer
    CANCELED = "CANCELED" # The document was replaced with a new version and this review is no longer needed.


class ApprovalModel(db.Model):
    __tablename__ = 'approval'
    id = db.Column(db.Integer, primary_key=True)
    study_id = db.Column(db.Integer, db.ForeignKey(StudyModel.id), nullable=False)
    study = db.relationship(StudyModel, backref='approval')
    workflow_id = db.Column(db.Integer, db.ForeignKey(WorkflowModel.id), nullable=False)
    workflow_version = db.Column(db.String)
    approver_uid = db.Column(db.String)  # Not linked to user model, as they may not have logged in yet.
    status = db.Column(db.String)
    message = db.Column(db.String)


class Approval(object):

    @classmethod
    def from_model(cls, model: ApprovalModel):
        instance = cls()

        instance.id = model.id
        instance.workflow_version = model.workflow_version
        instance.approver_uid = model.approver_uid
        instance.status = model.status
        instance.study_id = model.study_id
        if model.study:
            instance.title = model.study.title


class ApprovalSchema(ma.Schema):
    class Meta:
        model = Approval
        fields = ["id", "workflow_version", "approver_uid", "status",
                  "study_id", "title"]
        unknown = INCLUDE

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
