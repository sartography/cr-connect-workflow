from crc.api.common import ApiError
from crc.models.protocol_builder import ProtocolBuilderCreatorStudySchema
from crc.scripts.script import Script
from crc.services.protocol_builder import ProtocolBuilderService


class GetUserStudies(Script):

    def get_description(self):
        return """Returns a list of study ids for a user"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        user_id = None
        if len(args) > 0:
            user_id = args[0]
        elif 'user_id' in kwargs:
            user_id = kwargs['user_id']
        if user_id is not None:
            user_studies = ProtocolBuilderService().get_studies(user_id)
            results = ProtocolBuilderCreatorStudySchema(many=True).dump(user_studies)
            return results
