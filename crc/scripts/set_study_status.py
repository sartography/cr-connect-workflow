from crc import session
from crc.api.common import ApiError
from crc.models.study import StudyModel, StudyStatus
from crc.scripts.script import Script


class MyScript(Script):

    def get_description(self):
        return """This is my description"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):

        if 'status' in kwargs.keys():
            new_status = kwargs['status']
        elif len(args) > 0:
            new_status = args[0]
        else:
            raise ApiError.from_task(code='missing_argument',
                                     message='You must include the new status when calling `set_study_status` script. '
                                             'The new status can be `in_progress`, `hold`, `open_for_enrollment`, or `abandoned`.',
                                     task=task)
        if new_status in ['in_progress', 'hold', 'open_for_enrollment', 'abandoned']:
            return getattr(StudyStatus, new_status).value

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if 'status' in kwargs.keys():
            new_status = kwargs['status']
        elif len(args) > 0:
            new_status = args[0]
        else:
            raise ApiError.from_task(code='missing_argument',
                                     message='You must include the new status when calling `set_study_status` script. '
                                             'The new status can be `in_progress`, `hold`, `open_for_enrollment`, or `abandoned`.',
                                     task=task)
        study_model = session.query(StudyModel).filter(StudyModel.id == study_id).first()
        study_status = getattr(StudyStatus, new_status)
        study_model.status = study_status
        session.commit()

        print('set_study_status')

        return study_model.status.value
