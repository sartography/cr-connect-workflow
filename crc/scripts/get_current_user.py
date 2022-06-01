from crc.api.common import ApiError
from crc.models.user import UserModelSchema
from crc.scripts.script import Script
from crc.services.user_service import UserService


class GetCurrentUser(Script):

    def get_description(self):
        return """Returns the current user. 
                  If this is really an admin doing an impersonation, 
                  we also return information about the impersonator (the admin)"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return self.do_task(task, study_id, workflow_id, *args, **kwargs)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        if UserService.has_user():
            current_user = UserService.current_user(allow_admin_impersonate=True)
            if UserService.user_is_admin() and UserService.admin_is_impersonating():
                impersonator = UserService.get_impersonator()
                current_user.impersonator = impersonator
            current_user_data = UserModelSchema().dump(current_user)
            return current_user_data
        else:
            raise ApiError(code='no_has_user',
                           message='The current user is not logged in.')
