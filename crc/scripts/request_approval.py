from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.approval_service import ApprovalService


class RequestApproval(Script):
    """This still needs to be fully wired up as a Script task callable from the workflow
    But the basic logic is here just to get the tests passing and logic sound. """

    def get_description(self):
        return """
Creates an approval request on this workflow, by the given approver_uid(s),"
Takes multiple arguments, which should point to data located in current task
or be quoted strings. The order is important.  Approvals will be processed 
in this order.

Example:
RequestApproval approver1 "dhf8r"
"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.get_uids(task, args)

    def do_task(self,  task, study_id, workflow_id,  *args, **kwargs):
        uids = self.get_uids(task, args)
        if isinstance(uids, str):
            ApprovalService.add_approval(study_id, workflow_id, args)
        elif isinstance(uids, list):
            for id in uids:
                if id: ## Assure it's not empty or null
                    ApprovalService.add_approval(study_id, workflow_id, id)

    def get_uids(self, task, args):
        if len(args) < 1:
            raise ApiError(code="missing_argument",
                           message="The RequestApproval script requires at least one argument.  The "
                                   "the name of the variable in the task data that contains user"
                                   "id to process.  Multiple arguments are accepted.")
        uids = []
        for arg in args:
            id = task.workflow.script_engine.evaluate_expression(task, arg)
            uids.append(id)
            if not isinstance(id, str):
                raise ApiError(code="invalid_argument",
                               message="The RequestApproval script requires 1 argument.  The "
                                   "the name of the variable in the task data that contains user"
                                   "ids to process.  This must point to an array or a string, but "
                                   "it currently points to a %s " % uids.__class__.__name__)

        return uids

