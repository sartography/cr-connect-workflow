from crc import session
from crc.models.study import StudyModel
from crc.scripts.script import Script


class GetStudyProgressStatus(Script):

    def get_description(self):
        return """
        Get the progress status of the current study. 
        Progress status is only set when `status` is `in_progress`. 
        Progress status can be one of `in_progress`, `submitted_for_pre_review`, `in_pre_review`, `returned_from_pre_review`, `pre_review_complete`, `agenda_date_set`, `approved`, `approved_with_conditions`, `deferred`, or `disapproved`.
        """

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        progress_status = session.query(StudyModel.progress_status).filter(StudyModel.id == study_id).scalar()
        if progress_status:
            return progress_status.value
