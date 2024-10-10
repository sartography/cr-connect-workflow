from crc import app
from crc.api.common import ApiError
from crc.scripts.script import Script

import dateparser
import pytz


class GetLocaltime(Script):

    def get_description(self):
        return """Converts a UTC Datetime object into a Datetime object with a different timezone.
        Defaults to US/Eastern"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args) > 0 or 'timestamp' in kwargs:
            return self.do_task(task, study_id, workflow_id, *args, **kwargs)
        raise ApiError(code='missing_timestamp',
                       message='You must include a timestamp to convert.')

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args) > 0 or 'timestamp' in kwargs:
            if 'timestamp' in kwargs:
                timestamp = kwargs['timestamp']
            else:
                timestamp = args[0]
            if 'timezone' in kwargs:
                timezone = kwargs['timezone']
            elif len(args) > 1:
                timezone = args[1]
            else:
                timezone = 'US/Eastern'
            # with Python 3.9, not passing the timezone resuls in a  PytzUsageWarning usage warning.
            parsed_timestamp = dateparser.parse(timestamp, settings={'TIMEZONE': 'UTC'})
            try:
                localtime = parsed_timestamp.astimezone(pytz.timezone(timezone))
            except AttributeError as ae:
                # In general, we want this script to succeed. It is called during the document assembly process.
                # We want to generate the zip file and submit to the IRB, even if it has minor errors
                app.logger.info(f'Could not convert the timestamp to a localtime. Original error: {ae}')
                localtime = None
                # TODO: When we fix the frontend to no display errors on production, we can raise an error here.
                # raise ApiError(code='invalid_date_or_timestamp',
                #                message=f'We could not process the timestamp into a localtime. Original error: {ae}')
            return localtime

        else:
            raise ApiError(code='missing_timestamp',
                           message='You must include a timestamp to convert.')

