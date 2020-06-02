from flask import g

from crc import app, db, session

from crc.api.common import ApiError, ApiErrorSchema
from crc.models.approval import Approval, ApprovalModel, ApprovalSchema
from crc.services.approval_service import ApprovalService


def get_approvals(everything=False):
    if everything:
        db_approvals = ApprovalService.get_all_approvals()
    else:
        db_approvals = ApprovalService.get_approvals_per_user(g.user.uid)
    approvals = [Approval.from_model(approval_model) for approval_model in db_approvals]

    results = ApprovalSchema(many=True).dump(approvals)
    return results


def get_approvals_for_study(study_id=None):
    db_approvals = ApprovalService.get_approvals_for_study(study_id)
    approvals = [Approval.from_model(approval_model) for approval_model in db_approvals]
    results = ApprovalSchema(many=True).dump(approvals)
    return results


def update_approval(approval_id, body):
    if approval_id is None:
        raise ApiError('unknown_approval', 'Please provide a valid Approval ID.')

    approval_model = session.query(ApprovalModel).get(approval_id)
    if approval_model is None:
        raise ApiError('unknown_approval', 'The approval "' + str(approval_id) + '" is not recognized.')

    approval: Approval = ApprovalSchema().load(body)
    if approval_model.approver_uid != g.user.uid:
        raise ApiError("not_your_approval", "You may not modify this approval. It belongs to another user.")

    approval.update_model(approval_model)
    session.commit()

    result = ApprovalSchema().dump(approval)
    return result
