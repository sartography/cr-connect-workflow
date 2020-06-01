from datetime import datetime

from sqlalchemy import desc

from crc import db, session
from crc.api.common import ApiError

from crc.models.approval import ApprovalModel, ApprovalStatus, ApprovalFile
from crc.models.workflow import WorkflowModel
from crc.services.file_service import FileService


class ApprovalService(object):
    """Provides common tools for working with an Approval"""

    @staticmethod
    def get_approvals_per_user(approver_uid):
        """Returns a list of all approvals for the given user (approver)"""
        db_approvals = session.query(ApprovalModel).filter_by(approver_uid=approver_uid).all()
        return db_approvals

    @staticmethod
    def get_approvals_for_study(study_id):
        """Returns a list of all approvals for the given study"""
        db_approvals = session.query(ApprovalModel).filter_by(study_id=study_id).all()
        return db_approvals

    @staticmethod
    def get_all_approvals():
        """Returns a list of all approvlas"""
        db_approvals = session.query(ApprovalModel).all()
        return db_approvals

    @staticmethod
    def update_approval(approval_id, approver_uid, status):
        """Update a specific approval"""
        db_approval = session.query(ApprovalModel).get(approval_id)
        if db_approval:
            db_approval.status = status
            session.add(db_approval)
            session.commit()
        # TODO: Log update action by approver_uid - maybe ?
        return db_approval

    @staticmethod
    def add_approval(study_id, workflow_id, approver_uid):
        """we might have multiple approvals for a workflow, so I would expect this
            method to get called multiple times for the same workflow.  This will
            only add a new approval if no approval already exists for the approver_uid,
            unless the workflow has changed, at which point, it will CANCEL any
            pending approvals and create a new approval for the latest version
            of the workflow."""

        # Find any existing approvals for this workflow and approver.
        latest_approval_request = db.session.query(ApprovalModel). \
            filter(ApprovalModel.workflow_id == workflow_id). \
            filter(ApprovalModel.approver_uid == approver_uid). \
            order_by(desc(ApprovalModel.version)).first()

        # Construct as hash of the latest files to see if things have changed since
        # the last approval.
        workflow = db.session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        workflow_data_files = FileService.get_workflow_data_files(workflow_id)
        current_data_file_ids = list(data_file.id for data_file in workflow_data_files)

        if len(current_data_file_ids) == 0:
            raise ApiError("invalid_workflow_approval", "You can't create an approval for a workflow that has"
                                                        "no files to approve in it.")

        # If an existing approval request exists and no changes were made, do nothing.
        # If there is an existing approval request for a previous version of the workflow
        # then add a new request, and cancel any waiting/pending requests.
        if latest_approval_request:
            request_file_ids = list(file.file_data_id for file in latest_approval_request.approval_files)
            current_data_file_ids.sort()
            request_file_ids.sort()
            if current_data_file_ids == request_file_ids:
                return  # This approval already exists.
            else:
                latest_approval_request.status = ApprovalStatus.CANCELED.value
                db.session.add(latest_approval_request)
                version = latest_approval_request.version + 1
        else:
            version = 1

        model = ApprovalModel(study_id=study_id, workflow_id=workflow_id,
                              approver_uid=approver_uid, status=ApprovalStatus.PENDING.value,
                              message="", date_created=datetime.now(),
                              version=version)
        approval_files = ApprovalService._create_approval_files(workflow_data_files, model)
        db.session.add(model)
        db.session.add_all(approval_files)
        db.session.commit()

    @staticmethod
    def _create_approval_files(workflow_data_files, approval):
        """Currently based exclusively on the status of files associated with a workflow."""
        file_approval_models = []
        for file_data in workflow_data_files:
            file_approval_models.append(ApprovalFile(file_data_id=file_data.id,
                                                     approval=approval))
        return file_approval_models

