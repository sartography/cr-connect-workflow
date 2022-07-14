from SpiffWorkflow.bpmn.exceptions import WorkflowTaskExecException

from crc import session
from crc.api.common import ApiError
from crc.models.workflow import WorkflowModel, WorkflowStatus
from crc.scripts.script import Script


class MyScript(Script):

    def get_description(self):
        return """
Get the status of a workflow. 
Currently, status is one of "not_started", "user_input_required", "waiting", or "complete".

You must pass a workflow_id.

Examples:
    status = get_workflow_status(1)
    status = get_workflow_status(search_workflow_id=1)
"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if 'workflow_spec_id' in kwargs.keys() or len(args) > 0:
            return WorkflowStatus.not_started.value
        else:
            raise WorkflowTaskExecException(task, f'get_workflow_status() failed. You must include a workflow_spec_id'
                                                  f' when calling the `get_workflow_status` script.')

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if 'workflow_spec_id' in kwargs.keys() or len(args) > 0:
            if 'workflow_spec_id' in kwargs.keys():
                workflow_spec_id = kwargs['workflow_spec_id']
            else:
                workflow_spec_id = args[0]
            workflow_model = session.query(WorkflowModel). \
                filter(WorkflowModel.workflow_spec_id == workflow_spec_id). \
                filter(WorkflowModel.study_id == study_id).\
                first()
            if workflow_model:
                return workflow_model.status.value
            else:
                return WorkflowStatus.not_started.value

        else:
            raise WorkflowTaskExecException(task, f'get_workflow_status() failed. You must include a workflow_spec_id'
                                                  f' when calling the `get_workflow_status` script.')