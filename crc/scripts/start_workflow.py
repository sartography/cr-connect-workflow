from crc import session
from crc.api.common import ApiError
from crc.models.api_models import WorkflowApi, WorkflowApiSchema
from crc.models.workflow import WorkflowModel, WorkflowStatus
from crc.scripts.script import Script
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService


class StartWorkflow(Script):

    @staticmethod
    def get_workflow(workflow_id):
        workflow_model: WorkflowModel = session.query(WorkflowModel).filter_by(id=workflow_id).first()
        processor = WorkflowProcessor(workflow_model)

        processor.do_engine_steps()
        processor.save()
        WorkflowService.update_task_assignments(processor)

        workflow_api_model = WorkflowService.processor_to_workflow_api(processor)
        return WorkflowApiSchema().dump(workflow_api_model)

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

            # Optimization -> only do this if the workflow is not started.
            if workflow:
                workflow_api = self.get_workflow(workflow.id)
                return workflow_api
            else:
                raise ApiError(code='unknown_workflow',
                               message=f"We could not find a workflow with workflow_spec_id '{workflow_spec_id}'.")

        else:
            raise ApiError(code='missing_parameter',
                           message=f'The start_workflow script requires a workflow id')
