from crc import session
from flask_bpmn.api.common import ApiError
from crc.models.study import StudyModel, StudyStatus
from crc.scripts.script import Script


class SetStudyStatus(Script):
    @staticmethod
    def get_study_status_values():
        study_status_values = []
        for item in StudyStatus:
            study_status_values.append(item.value)
        return study_status_values

    def get_description(self):
        study_status_values = self.get_study_status_values()
        return f"Set the study status. Requires a study status. Study status must be in {study_status_values}."

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        study_status_values = self.get_study_status_values()
        if len(args) == 1:
            if args[0] in study_status_values:
                return True
            else:
                raise ApiError(code='bad_parameter',
                               message=f"The set_study_status script requires 1 parameter, from 'in_progress', 'hold', 'open_for_enrollment', 'abandoned', or 'cr_connect_complete'. You sent: {args[0]}.")
        else:
            raise ApiError(code='bad_parameter_count',
                           message=f'The set_study_status script requires 1 parameter, {len(args)} were given.')

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        study_status_values = self.get_study_status_values()
        if len(args) == 1:
            if args[0] in study_status_values:
                study = session.query(StudyModel).filter(StudyModel.id==study_id).first()
                study.status = StudyStatus(args[0]).value
                session.commit()
