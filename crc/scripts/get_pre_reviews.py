from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.protocol_builder import ProtocolBuilderService


class GetPreReviews(Script):

    def get_description(self):
        return """Returns information about submissions returned to PI during study Pre Review"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        pre_reviews = ProtocolBuilderService().get_pre_reviews(study_id)
        if pre_reviews:
            return pre_reviews
        else:
            raise ApiError(code='pb_error',
                           message=f'There was a problem retrieving Pre Reviews for study `{study_id}`. Nothing was returned from Protocol Builder.')
