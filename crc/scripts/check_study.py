from SpiffWorkflow.exceptions import WorkflowTaskExecException

from crc.scripts.script import Script
from flask_bpmn.api.api_error import ApiError
from crc.services.protocol_builder import ProtocolBuilderService
from crc.services.study_service import StudyService
from crc.services.workflow_spec_service import WorkflowSpecService


class CheckStudy(Script):

    pb = ProtocolBuilderService()

    def get_description(self):
        return """Returns the Check Study data for a Study"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        spec_service = WorkflowSpecService()
        categories = spec_service.get_categories()
        study = StudyService.get_study(study_id, categories)
        if study:
            return {"DETAIL": "Passed validation.", "STATUS": "No Error"}
        else:
            raise WorkflowTaskExecException(task, 'Function check_study failed. There is no study for study_id {study_id}.')

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        check_study = self.pb.check_study(study_id)
        if check_study:
            return check_study
        else:
            raise WorkflowTaskExecException(task, 'There was a problem checking information for this study.')
