from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.study_service import StudyService


class UpdateStudyAssociates(Script):

    argument_error_message = "You must supply at least one argument to the " \
                             "update_study_associates task, an array of objects in the form " \
                             "{'uid':'someid', 'role': 'text', 'send_email: 'boolean', " \
                             "'access':'boolean'} "


    def get_description(self):
        return """
Allows you to associate other users with a study - only 'uid' is required in the 
incoming dictionary, but will be useless without other information - all values will default to 
false or blank

An empty list will delete the existing Associated list (except owner)

Each UID will be validated vs ldap and will raise an error if the uva_uid is not found. This supplied list will replace 
any 
associations already in place. 

example : update_study_associates([{'uid':'sbp3ey','role':'Unicorn Herder', 'send_email': False, 'access':True}]) 

"""
    def validate_arg(self,arg):
        if not isinstance(arg,list):
            raise ApiError("invalid parameter", "This function is expecting a list of dictionaries")
        if not len(arg) > 0 and not isinstance(arg[0],dict):
            raise ApiError("invalid paramemter","This function is expecting a list of dictionaries")

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        items = args[0]
        self.validate_arg(items)
        return all([x.get('uid',False) for x in items])


    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        access_list = args[0]
        self.validate_arg(access_list)
        return StudyService.update_study_associates(study_id,access_list)

