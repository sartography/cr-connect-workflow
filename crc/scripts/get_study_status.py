from crc import session
from crc.models.study import StudyModel
from crc.scripts.script import Script


class StudyStatus(Script):

    def get_description(self):
        return """Get the status of the current study. 
        Status can be one of `in_progress`, `hold`, `open_for_enrollment`, or `abandoned`."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        study_status = session.query(StudyModel.status).filter(StudyModel.id == study_id).scalar()
        if study_status:
            return study_status.value
