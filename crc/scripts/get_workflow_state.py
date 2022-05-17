from crc import session
from crc.api.common import ApiError
from crc.models.workflow import WorkflowModel
from crc.scripts.script import Script


class GetWorkflowState(Script):

    def get_description(self):
        return """Return the state and state_message for a workflow.
        Example: {'state': 'required', 'message': 'This workflow is required.'}"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        workflow_spec_id = None

        if 'workflow_spec_id' in kwargs:
            workflow_spec_id = kwargs['workflow_spec_id']
        elif len(args) > 0:
            workflow_spec_id = args[0]

        if workflow_spec_id:
            workflow = session.query(WorkflowModel).\
                filter(WorkflowModel.study_id == study_id).\
                filter(WorkflowModel.workflow_spec_id == workflow_spec_id).\
                first()

            if workflow:
                workflow_state = {'state': workflow.state, 'message': workflow.state_message}
            else:
                raise ApiError(code='no_workflow_found',
                               message=f'We could not find a workflow with workflow_spec_id: {workflow_spec_id}.')

        else:
            raise ApiError(code='missing_workflow_spec_id',
                           message='You must pass a workflow_spec_id to the get_workflow_state script.')

        return workflow_state
