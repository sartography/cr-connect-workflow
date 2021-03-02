from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.study_service import StudyService


class GetStudyAssociates(Script):

    argument_error_message = "You must supply at least one argument to the " \
                             "update_study_associates task, an array of objects in the form " \
                             "{'uid':'someid', 'role': 'text', 'send_email: 'boolean', " \
                             "'access':'boolean'} "


    def get_description(self):
        return """
Returns all people associated with the study - Will always return the study owner as assocated
example : get_study_associates() => [{'uid':'sbp3ey','role':'Unicorn Herder', 'send_email': False, 'access':True}] 

"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        return True


    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        return StudyService.get_study_associates(study_id)

