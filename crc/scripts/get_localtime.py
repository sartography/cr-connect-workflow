from crc.scripts.script import Script
from crc.api.common import ApiError


class GetLocaltime(Script):

    def get_description(self):
        return """Converts a UTC Datetime object into a Datetime object with a different timezone.
        Defaults to US/Eastern"""

    def do_task_validate_only(self, task, study_id, workflow_id, **kwargs):
        if len(kwargs):
            return True
        raise ApiError(code='missing_timestamp',
                       message='You must include a timestamp to convert.')

    def do_task(self, task, study_id, workflow_id, **kwargs):
        pass

