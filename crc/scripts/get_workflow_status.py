from crc import session
from crc.api.common import ApiError
from crc.models.workflow import WorkflowModel
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
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if 'search_workflow_id' in kwargs.keys() or len(args) > 0:
            if 'search_workflow_id' in kwargs.keys():
                search_workflow_id = kwargs['search_workflow_id']
            else:
                search_workflow_id = args[0]
            workflow_model = session.query(WorkflowModel).filter(WorkflowModel.id == search_workflow_id).first()
            if workflow_model:
                return workflow_model.status.value
            else:
                return f'No model found for workflow {search_workflow_id}.'

        else:
            raise ApiError.from_task(code='missing_argument',
                                     message='You must include a workflow_id when calling the `get_workflow_status` script.',
                                     task=task)
