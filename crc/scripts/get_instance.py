from crc import app
from crc.scripts.script import Script


class GetInstance(Script):

    def get_description(self):
        return """Get the name of the current instance, using the SERVER_NAME environment variable."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if 'SERVER_NAME' in app.config:
            return app.config['SERVER_NAME']
        # TODO: Not sure what we should do here
        app.logger.info('no_server_name: SERVER_NAME not configured for this server.')
        return ''
