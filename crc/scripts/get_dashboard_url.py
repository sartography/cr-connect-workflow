from crc.scripts.script import Script
from crc import app


class GetDashboardURL(Script):

    def get_description(self):
        """Get the URL for the main dashboard. This should be system instance aware.
        I.e., dev, testing, production, etc."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        frontend = app.config['FRONTEND']
        return f'http://{frontend}'
