from SpiffWorkflow.bpmn.exceptions import WorkflowTaskExecException

from crc import session
from crc.api.common import ApiError
from crc.models.study import StudyModel, ProgressStatus
from crc.scripts.script import Script


class SetStudyProgressStatus(Script):

    def get_description(self):
        return """Set the progress status of the current study. 
        Progress status can be one of `in_progress`, `submitted_for_pre_review`, `in_pre_review`, `returned_from_pre_review`, `pre_review_complete`, `agenda_date_set`, `approved`, `approved_with_conditions`, `deferred`, or `disapproved`."""

    def get_status(self, task, *args, **kwargs):
        if 'new_status' in kwargs.keys() or len(args) > 0:
            if 'new_status' in kwargs.keys():
                new_status = kwargs['new_status']
            else:
                new_status = args[0]
            try:
                progress_status = getattr(ProgressStatus, new_status)
            except AttributeError as ae:
                raise WorkflowTaskExecException(task, f"set_study_progress_status().  Could not find a status matching"
                                                      f" `{new_status}`. Original message: {ae}")
            return progress_status
        else:
            raise WorkflowTaskExecException(task, f"set_study_progress_status() failed You must include the new"
                                                  f" progress status when calling `set_study_progress_status` script.")

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.get_status(task, *args, **kwargs).value

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        study_model = session.query(StudyModel).filter(StudyModel.id == study_id).first()
        study_model.progress_status = self.get_status(task, *args, **kwargs)
        session.commit()
        return study_model.progress_status.value
