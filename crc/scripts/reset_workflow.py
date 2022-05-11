from crc import session
from flask_bpmn.api.api_error import ApiError
from crc.models.workflow import WorkflowModel, WorkflowSpecInfo
from crc.scripts.script import Script
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_spec_service import WorkflowSpecService


class ResetWorkflow(Script):

    def get_description(self):
        return """Reset a workflow. Run by mas vftgv ter workflow.
            Designed for completed workflows where we need to force rerunning the workflow.
            I.e., a new PI"""

    def get_spec(self, *args, **kwargs):
        workflow_spec_id = None
        if 'workflow_spec_id' in kwargs.keys():
            workflow_spec_id = kwargs['workflow_spec_id']
        elif len(args) > 0:
            workflow_spec_id = args[0]

        if not workflow_spec_id:
            raise ApiError(code='missing_workflow_id',
                           message='Reset workflow requires a workflow_spec_id')

        workflow_spec = WorkflowSpecService().get_spec(workflow_spec_id)
        if not workflow_spec:
            raise ApiError(code='missing_workflow_spec',
                           message=f'No workflow spec found with the \
                                    id: {workflow_spec_id}')

        return workflow_spec

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.get_spec(*args, **kwargs)  # Just assure we can find the workflow spec.

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if 'clear_data' in kwargs.keys():
            clear_data = bool(kwargs['clear_data'])
        else:
            clear_data = False

        workflow_spec = self.get_spec(*args, **kwargs)
        if workflow_spec:
            workflow_model: WorkflowModel = session.query(WorkflowModel).filter_by(
                workflow_spec_id=workflow_spec.id,
                study_id=study_id).first()
            if workflow_model:
                WorkflowProcessor.reset(workflow_model, clear_data=clear_data)
