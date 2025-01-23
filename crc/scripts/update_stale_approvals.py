from crc.api.common import ApiError
from crc.models.workflow import WorkflowModel
from crc.scripts.script import Script
from crc import session
from crc.models.task_event import TaskEventModel
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService


class UpdateStaleApprovals(Script):

    def get_description(self):
        return """We use this script to clean up task events when IDS Approvals are no longer required. 
        When PB changes and an Approval goes from required to not required, 
        Approvals show up in user dashboards that are no longer valid. 
        This script deletes the associated task events. """

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        """This script is called by the top_level_workflow.
        It should only be called when an approval is no longer required.
        To be safe, we test for the condition before deleting the task events.

        It requires 2 inputs; the workflow and the document that determines if the approval is required."""
        workflow = kwargs['workflow']
        document = kwargs['document']
        documents = task.data['study_info']('documents')
        is_required = documents[document]['required']
        if not is_required:
            WorkflowService.delete_stale_assignments(study_id, workflow)

        return is_required, workflow, document
