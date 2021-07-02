from crc.scripts.script import Script
from crc.api.common import ApiError
from crc.services.protocol_builder import ProtocolBuilderService


class CheckStudy(Script):

    pb = ProtocolBuilderService()

    def get_description(self):
        pass

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        pass

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        check_study = self.pb.check_study(study_id)
        if check_study:
            return check_study
        else:
            raise ApiError.from_task(code='missing_check_study',
                                     message='There was a problem checking information for this study.',
                                     task=task)
