from crc import session
from crc.api.common import ApiError
from crc.models.workflow import WorkflowModel, WorkflowSpecModel
from crc.scripts.script import Script
from crc.services.workflow_processor import WorkflowProcessor


class ResetWorkflow(Script):

    def get_description(self):
        return """Reset a workflow. Run by master workflow.
            Designed for completed workflows where we need to force rerunning the workflow.
            I.e., a new PI"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return hasattr(kwargs, 'workflow_name')

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        if 'workflow_name' in kwargs.keys():
            workflow_name = kwargs['workflow_name']
            workflow_spec: WorkflowSpecModel = session.query(WorkflowSpecModel).filter_by(name=workflow_name).first()
            if workflow_spec:
                workflow_model: WorkflowModel = session.query(WorkflowModel).filter_by(
                    workflow_spec_id=workflow_spec.id,
                    study_id=study_id).first()
                if workflow_model:
                    workflow_processor = WorkflowProcessor.reset(workflow_model, clear_data=False, delete_files=False)
                    return workflow_processor
                else:
                    raise ApiError(code='missing_workflow_model',
                                   message=f'No WorkflowModel returned. \
                                            workflow_spec_id: {workflow_spec.id} \
                                            study_id: {study_id}')
            else:
                raise ApiError(code='missing_workflow_spec',
                               message=f'No WorkflowSpecModel returned. \
                                        name: {workflow_name}')
        else:
            raise ApiError(code='missing_workflow_name',
                           message='Reset workflow requires a workflow name')
