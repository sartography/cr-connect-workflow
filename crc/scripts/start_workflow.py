from crc import session
from crc.api.common import ApiError
from crc.api.workflow import get_workflow
from crc.models.api_models import WorkflowApi, WorkflowApiSchema
from crc.models.workflow import WorkflowModel, WorkflowStatus
from crc.scripts.script import Script


class StartWorkflow(Script):

    def get_description(self):
        return """Script to start a workflow programmatically.
        It requires a workflow_spec_id.
        It accepts the workflow_spec_id as a positional argument 
        or with the keyword 'workflow_spec_id'"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args) == 1 or 'workflow_spec_id' in kwargs:
            if 'workflow_spec_id' in kwargs:
                workflow_spec_id = kwargs['workflow_spec_id']
            else:
                workflow_spec_id = args[0]

            workflow_api = WorkflowApi(1234,
                                       WorkflowStatus('user_input_required'),
                                       'next_task',
                                       'navigation',
                                       workflow_spec_id,
                                       'total_tasks',
                                       'completed_tasks',
                                       'last_updated',
                                       'is_review',
                                       'title',
                                       study_id)
            return WorkflowApiSchema().dump(workflow_api)

        else:
            raise ApiError(code='missing_parameter',
                           message=f'The start_workflow script requires a workflow id')

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args) == 1 or 'workflow_spec_id' in kwargs:
            if 'workflow_spec_id' in kwargs:
                workflow_spec_id = kwargs['workflow_spec_id']
            else:
                workflow_spec_id = args[0]

            workflow = session.query(WorkflowModel).\
                filter(WorkflowModel.study_id==study_id).\
                filter(WorkflowModel.workflow_spec_id==workflow_spec_id).\
                first()
            workflow_api = get_workflow(workflow.id)

            return workflow_api

        else:
            raise ApiError(code='missing_parameter',
                           message=f'The start_workflow script requires a workflow id')
