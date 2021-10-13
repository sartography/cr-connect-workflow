from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.study_service import StudyService


class UpdateStudyAssociates(Script):

    argument_error_message = "You must supply at least one argument to the " \
                             "update_study_associates task, an array of objects in the form " \
                             "{'uid':'someid', 'role': 'text', 'send_email: 'boolean', " \
                             "'access':'boolean'} "


    def get_description(self):
        return """Allows you to associate other users with a study - only 'uid' is a required keyword argument


An empty list will delete the existing Associated list (except owner)

The UID will be validated vs ldap and will raise an error if the uva_uid is not found. This will replace any  
association already in place for this user.

example : update_study_associate(uid='sbp3ey',role='Unicorn Herder',send_email=False, access=True) 

"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if kwargs.get('uid') is None:
            raise ApiError('uid_is_required_argument','a valid keyword argument of uid is required, it should be the '
                                                      'uva uid for this user')
        return True



    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        return StudyService.update_study_associate(study_id=study_id,**kwargs)

