from SpiffWorkflow.bpmn.exceptions import WorkflowTaskExecException

from crc import session
from crc.api.common import ApiError
from crc.models.api_models import WorkflowApi, WorkflowApiSchema
from crc.models.workflow import WorkflowModel, WorkflowStatus
from crc.scripts.script import Script
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService


class StartWorkflow(Script):

    def get_description(self):
        return """Script to start a workflow programmatically.
        It requires a workflow_spec_id.
        It accepts the workflow_spec_id as a positional argument 
        or with the keyword 'workflow_spec_id'"""

    def get_workflow(self, study_id, *args, **kwargs):
        if len(args) == 1 or 'workflow_spec_id' in kwargs:
            if 'workflow_spec_id' in kwargs:
                workflow_spec_id = kwargs['workflow_spec_id']
            else:
                workflow_spec_id = args[0]
        else:
            raise ApiError(code='missing_parameter',
                           message=f'The start_workflow script requires a workflow id')

        workflow = session.query(WorkflowModel). \
            filter(WorkflowModel.study_id == study_id). \
            filter(WorkflowModel.workflow_spec_id == workflow_spec_id). \
            first()

        if not (workflow):
            raise ApiError(code='unknown_workflow',
                           message=f"We could not find a workflow with workflow_spec_id '{workflow_spec_id}'.")

        return workflow

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.get_workflow(study_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        workflow_model = self.get_workflow(study_id, *args, **kwargs)
        if workflow_model.status != WorkflowStatus.not_started:
            return  # This workflow has al ready started, don't execute these next very expensive lines.
        try:
            processor = WorkflowProcessor(workflow_model)
            processor.do_engine_steps()
            processor.save()
            WorkflowService.update_task_assignments(processor)
        except ApiError as e:
            msg = f"Failed to execute start_workflow('{workflow_model.workflow_spec_id}'). " + e.message
            te = WorkflowTaskExecException(task, msg)
            raise te
