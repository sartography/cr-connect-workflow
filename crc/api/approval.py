from crc.models.approval import ApprovalModel, Approval


def get_approvals(approver_uid = None):
    approval_model = ApprovalModel()
    approval = Approval.from_model(approval_model)
    return {}

def update_approval(approval_id):
    return {}