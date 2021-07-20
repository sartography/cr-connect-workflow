from crc.scripts.script import Script
from crc.api.common import ApiError
from crc.services.protocol_builder import ProtocolBuilderService
from crc.services.study_service import StudyService


class CheckStudy(Script):

    pb = ProtocolBuilderService()

    def get_description(self):
        return """Returns the Check Study data for a Study"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        study = StudyService.get_study(study_id)
        if study:
            return {"DETAIL": "Passed validation.", "STATUS": "No Error"}
        else:
            raise ApiError.from_task(code='bad_study',
                                     message=f'No study for study_id {study_id}',
                                     task=task)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        check_study = self.pb.check_study(study_id)
        if check_study:
            return check_study
        else:
            raise ApiError.from_task(code='missing_check_study',
                                     message='There was a problem checking information for this study.',
                                     task=task)
