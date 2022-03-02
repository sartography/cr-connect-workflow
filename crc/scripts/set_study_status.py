from crc import session
from crc.api.common import ApiError
from crc.models.study import StudyModel, StudyStatus
from crc.scripts.script import Script


class SetStudyStatus(Script):

    def get_description(self):
        return """Set the study status.
        Requires 'in_progress', 'hold', 'open_for_enrollment', 'abandoned', or 'cr_connect_complete'."""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args) == 1:
            if args[0] in ['in_progress', 'hold', 'open_for_enrollment', 'abandoned', 'cr_connect_complete']:
                return True
            else:
                raise ApiError(code='bad_parameter',
                               message=f"The set_study_status script requires 1 parameter, from 'in_progress', 'hold', 'open_for_enrollment', 'abandoned', or 'cr_connect_complete'. You sent: {args[0]}.")
        else:
            raise ApiError(code='bad_parameter_count',
                           message=f'The set_study_status script requires 1 parameter, {len(args)} were given.')

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args) == 1:
            if args[0] in ['in_progress', 'hold', 'open_for_enrollment', 'abandoned', 'cr_connect_complete']:
                study = session.query(StudyModel).filter(StudyModel.id==study_id).first()
                study.status = StudyStatus(args[0]).value
                session.commit()
        print('SetStudyStatus')
