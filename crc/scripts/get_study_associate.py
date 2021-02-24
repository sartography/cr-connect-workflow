from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.study_service import StudyService


class GetStudyAssociates(Script):



    def get_description(self):
        return """
Returns person assocated with study or an error if one is not associated.
example : get_study_associate('sbp3ey') => {'uid':'sbp3ey','role':'Unicorn Herder', 'send_email': False, 
'access':True}

"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args)<1:
            return False
        return True


    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if len(args<1):
            raise ApiError('no_user_id_specified', 'A uva uid is the sole argument to this function')
        if not isinstance([0],type('')):
            raise ApiError('argument_should_be_string', 'A uva uid is always a string, please check type')
        return StudyService.get_study_associate(study_id=study_id,uid=args[0])


