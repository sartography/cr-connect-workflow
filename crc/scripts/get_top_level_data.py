from crc import session
from crc.api.common import ApiError
from crc.models.study import StudyModel
from crc.scripts.script import Script
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_spec_service import WorkflowSpecService


class GetTopLevelData(Script):

    def get_description(self):
        return """This is my description"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        spec_service = WorkflowSpecService()
        study_model = session.query(StudyModel).filter(StudyModel.id == study_id).first()

        try:
            master_workflow_results = WorkflowProcessor.run_master_spec(spec_service.master_spec, study_model)
        except Exception as e:
            raise ApiError("error_running_master_spec", f"Error running master spec: {str(e)}")

        return master_workflow_results
