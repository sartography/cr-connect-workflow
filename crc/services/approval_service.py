from crc import db, session, app

from crc.models.approval import ApprovalModel


class ApprovalService(object):
    """Provides common tools for working with an Approval"""

    @staticmethod
    def get_approvals_per_user(approver_uid):
        """Returns a list of all approvals for the given user (approver)"""
        db_approvals = session.query(ApprovalModel).filter_by(approver_uid=approver_uid).all()
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
