from crc.api.common import ApiError
from crc.models.workflow import WorkflowSpecInfoSchema
from crc.scripts.script import Script
from crc.services.workflow_spec_service import WorkflowSpecService


class GetSpecFromID(Script):

    def get_description(self):
        return """Get workflow spec information from a workflow spec id"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args) < 1:
            raise ApiError(code='missing_spec_id',
                           message='The get_spec_from_id script requires a spec_id.')
        spec_id = args[0]
        workflow_spec = WorkflowSpecService().get_spec(spec_id)

        return WorkflowSpecInfoSchema().dump(workflow_spec)
