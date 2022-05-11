from flask_bpmn.api.api_error import ApiError
from crc.scripts.script import Script


class DeleteVariables(Script):

    def get_description(self):
        return """Script to delete variables from task_data, if they exist.
        Accepts a list of variables to delete."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        for arg in args:
            if arg in task.data:
                del(task.data[arg])
