import urllib

from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.reference_file_service import ReferenceFileService
import flask
from crc import app


class ReferenceFileUrl(Script):

    def get_description(self):
        return """This is my description"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        token = 'not_available'
        if len(args) > 0:
            server_name = app.config.get('SERVER_NAME')
            application_root = app.config.get('APPLICATION_ROOT', '/')
            reference_file_name = args[0]
            file_url = f"{server_name}{application_root}v1.0/reference_file/{reference_file_name}/data"
            if hasattr(flask.g, 'user'):
                token = flask.g.user.encode_auth_token()
            # url = file_url + '?auth_token=' + urllib.parse.quote_plus(token)
            if ('DEVELOPMENT' in app.config and app.config['DEVELOPMENT'] is True):
                prefix = 'http://'
            else:
                prefix = 'https://'
            url = f"{prefix}{file_url}?auth_token={urllib.parse.quote_plus(token)}"
            return url
        else:
            raise ApiError('missing_parameter', 'Please specify a reference file name.')
