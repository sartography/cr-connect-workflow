from datetime import datetime

from sqlalchemy import desc

from crc import db
from crc.models.approval import ApprovalModel, ApprovalStatus, ApprovalFile
from crc.scripts.script import Script
from crc.services.file_service import FileService


class RequestApproval(Script):
    """This still needs to be fully wired up as a Script task callable from the workflow
    But the basic logic is here just to get the tests passing and logic sound. """

    def get_description(self):
        return "Creates an approval request on this workflow, by the given approver_uid"

    def add_approval(self, study_id, workflow_id, approver_uid):
        """we might have multiple approvals for a workflow, so I would expect this
        method to get called many times."""

        # Find any existing approvals for this workflow and approver.
        latest_approval_request = db.session.query(ApprovalModel).\
            filter(ApprovalModel.workflow_id == workflow_id). \
            filter(ApprovalModel.approver_uid == approver_uid). \
            order_by(desc(ApprovalModel.version)).first()

        # Construct as hash of the latest files to see if things have changed since
        # the last approval.
        latest_files = FileService.get_workflow_files(workflow_id)
        current_workflow_hash = self.generate_workflow_hash(latest_files)

        # If an existing approval request exists and no changes were made, do nothing.
        # If there is an existing approval request for a previous version of the workflow
        # then add a new request, and cancel any waiting/pending requests.
        if latest_approval_request:
            # We could just compare the ApprovalFile lists here and do away with this hash.
            if latest_approval_request.workflow_hash == current_workflow_hash:
                return  # This approval already exists.
            else:
                latest_approval_request.status = ApprovalStatus.CANCELED.value
                db.session.add(latest_approval_request)
                version = latest_approval_request.version + 1
        else:
            version = 1

        model = ApprovalModel(study_id=study_id, workflow_id=workflow_id,
                              approver_uid=approver_uid, status=ApprovalStatus.WAITING.value,
                              message="", date_created=datetime.now(),
                              version=version, workflow_hash=current_workflow_hash)
        approval_files = self.create_approval_files(latest_files, model)
        db.session.add(model)
        db.session.add_all(approval_files)
        db.session.commit()

    def create_approval_files(self, files, approval):
        """Currently based exclusively on the status of files associated with a workflow."""
        file_approval_models = []
        for file in files:
            file_approval_models.append(ApprovalFile(file_id=file.id,
                                                     approval=approval,
                                                     file_version=file.latest_version))
        return file_approval_models

    def generate_workflow_hash(self, files):
        """Currently based exclusively on the status of files associated with a workflow."""
        version_array = []
        for file in files:
            version_array.append(str(file.id) + "[" + str(file.latest_version) + "]")
        full_version = "-".join(version_array)
        return full_version
