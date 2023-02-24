from crc.scripts.script import Script


class GetStudyID(Script):

    def get_description(self):
        return """This script returns the current study_id"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        return study_id
