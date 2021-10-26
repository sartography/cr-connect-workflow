from crc.api.common import ApiError
from crc.scripts.script import Script

import dateparser
import pytz


class GetLocaltime(Script):

    def get_description(self):
        return """Converts a UTC Datetime object into a Datetime object with a different timezone.
        Defaults to US/Eastern"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if 'timestamp' in kwargs:
            return self.do_task(task, study_id, workflow_id, *args, **kwargs)
        raise ApiError(code='missing_timestamp',
                       message='You must include a timestamp to convert.')

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if 'timestamp' in kwargs:
            timestamp = kwargs['timestamp']
            if 'timezone' in kwargs:
                timezone = kwargs['timezone']
            else:
                timezone = 'US/Eastern'
            parsed_timestamp = dateparser.parse(timestamp)
            localtime = parsed_timestamp.astimezone(pytz.timezone(timezone))
            return localtime

        else:
            raise ApiError(code='missing_timestamp',
                           message='You must include a timestamp to convert.')

