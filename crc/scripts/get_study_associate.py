from crc.api.common import ApiError
from crc.models.study import StudyAssociatedSchema
from crc.scripts.script import Script
from crc.services.study_service import StudyService


class GetStudyAssociate(Script):



    def get_description(self):
        return """Returns how a single person is associated with a study and what access they need,
 or raises an error if the person is not associated with the study.
example : get_study_associate('sbp3ey') => {'uid':'sbp3ey','role':'Unicorn Herder', 'send_email': False, 
'access':True}

"""
    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args) < 1:
            raise ApiError('no_user_id_specified', 'A uva uid is the sole argument to this function')
        return {'uid': 'sbp3ey', 'role': 'Unicorn Herder', 'send_email': False, 'access': True}

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args) < 1:
            raise ApiError('no_user_id_specified', 'A uva uid is the sole argument to this function')
        if not isinstance(args[0], str):
            raise ApiError('argument_should_be_string', 'A uva uid is always a string, please check type')
        associate = StudyService.get_study_associate(study_id=study_id, uid=args[0])
        return StudyAssociatedSchema().dump(associate)
