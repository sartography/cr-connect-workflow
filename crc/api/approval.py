from crc.api.common import ApiError, ApiErrorSchema
from crc.models.approval import Approval, ApprovalModel, ApprovalSchema
from crc.services.approval_service import ApprovalService


def get_approvals(approver_uid = None):
    db_approvals = ApprovalService.get_all_approvals()
    approvals = [Approval.from_model(approval_model) for approval_model in db_approvals]
    results = ApprovalSchema(many=True).dump(approvals)
    return results

def update_approval(approval_id, body):
    if approval_id is None:
        raise ApiError('unknown_approval', 'Please provide a valid Approval ID.')

    approver_uid = body.get('approver_uid')
    status = body.get('status')

    if approver_uid is None:
        raise ApiError('bad_formed_approval', 'Please provide a valid Approver UID')
    if status is None:
        raise ApiError('bad_formed_approval', 'Please provide a valid status for approval update')

    db_approval = ApprovalService.update_approval(approval_id, approver_uid, status)
    if db_approval is None:
        raise ApiError('unknown_approval', 'The approval "' + str(approval_id) + '" is not recognized.')

    approval = Approval.from_model(db_approval)
    result = ApprovalSchema().dump(approval)
    return result
