from crc import session
from flask_bpmn.api.common import ApiError
from crc.models.workflow import WorkflowModel, WorkflowSpecInfo, WorkflowSpecInfoSchema  # WorkflowSpecModel, WorkflowSpecModelSchema
from crc.scripts.script import Script
from crc.services.workflow_spec_service import WorkflowSpecService


class GetSpecFromWorkflowID(Script):

    def get_description(self):
        return """Get a workflow spec, from a workflow id. You must pass in a workflow id."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args) < 1:
            raise ApiError(code='missing_parameter',
                           message='Please pass in a workflow_id to use in the search.')
        passed_workflow_id = args[0]
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id == passed_workflow_id).first()
        workflow_spec = WorkflowSpecService().get_spec(workflow.workflow_spec_id)
        if workflow_spec:
            return WorkflowSpecInfoSchema().dump(workflow_spec)
