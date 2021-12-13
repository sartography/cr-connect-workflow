from crc import session
from crc.api.common import ApiError
from crc.models.study import StudyModel, ProgressStatus
from crc.scripts.script import Script


class SetStudyProgressStatus(Script):

    def get_description(self):
        return """Set the progress status of the current study. 
        Progress status can be one of `in_progress`, `submitted_for_pre_review`, `in_pre_review`, `returned_from_pre_review`, `pre_review_complete`, `agenda_date_set`, `approved`, `approved_with_conditions`, `deferred`, or `disapproved`."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):

        if 'new_status' in kwargs.keys() or len(args) > 0:
            if 'new_status' in kwargs.keys():
                new_status = kwargs['new_status']
            else:
                new_status = args[0]

            try:
                progress_status = getattr(ProgressStatus, new_status)

            except AttributeError as ae:
                raise ApiError.from_task(code='invalid_argument',
                                         message=f"We could not find a status matching `{new_status}`. Original message: {ae}",
                                         task=task)
            return progress_status.value

        else:
            raise ApiError.from_task(code='missing_argument',
                                     message='You must include the new status when calling `set_study_progress_status` script. '
                                             'The new status must be one of `in_progress`, `hold`, `open_for_enrollment`, or `abandoned`.',
                                     task=task)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        # Get new status
        if 'new_status' in kwargs.keys() or len(args) > 0:
            if 'new_status' in kwargs.keys():
                new_status = kwargs['new_status']
            else:
                new_status = args[0]

            # Get ProgressStatus object for new_status
            try:
                progress_status = getattr(ProgressStatus, new_status)

            # Invalid argument
            except AttributeError as ae:
                raise ApiError.from_task(code='invalid_argument',
                                         message=f"We could not find a status matching `{new_status}`. Original message: {ae}.",
                                         task=task)

            # Set new status
            study_model = session.query(StudyModel).filter(StudyModel.id == study_id).first()
            study_model.progress_status = progress_status
            session.commit()

            return study_model.progress_status.value

        # Missing argument
        else:
            raise ApiError.from_task(code='missing_argument',
                                     message='You must include the new progress status when calling `set_study_progress_status` script. ',
                                     task=task)

