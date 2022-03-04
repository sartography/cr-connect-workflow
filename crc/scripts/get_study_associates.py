from crc.models.study import StudyAssociatedSchema
from crc.scripts.script import Script
from crc.services.study_service import StudyService


class GetStudyAssociates(Script):

    def get_description(self):
        return """Returns all people associated with the study - Will always return the study owner as assocated
example : get_study_associates() => [{'uid':'sbp3ey','role':'Unicorn Herder', 'send_email': False, 'access':True}] 

"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if study_id:
            return self.do_task(task, study_id, workflow_id, args, kwargs)
        else:
            study_associates = [
                {'uid': 'dhf8r', 'role': 'Department Chair', 'send_email': True, 'access': True,
                 'ldap_info': {
                        'uid': 'dhf8r',
                        'display_name': "Dan Funk",
                         'email_address': 'dhf8r@virginia.edu',
                         'telephone_number': '',
                         'title': '',
                         'department': '',
                         'affiliation': '',
                        'sponsor_type': '',
                 }},
                {'uid': 'lb3dp', 'role': 'Primary Investigator', 'send_email': True, 'access': True,
                 'ldap_info': {
                     'uid': 'dhf8r',
                     'display_name': "Dan Funk",
                     'email_address': 'dhf8r@virginia.edu',
                     'telephone_number': '',
                     'title': '',
                     'department': '',
                     'affiliation': '',
                     'sponsor_type': ''
                 }},
                {'uid': 'lb3dp', 'role': 'Study Coordinator I', 'send_email': True, 'access': True,
                 'ldap_info': {
                     'uid': 'dhf8r',
                     'display_name': "Dan Funk",
                     'email_address': 'dhf8r@virginia.edu',
                     'telephone_number': '',
                     'title': '',
                     'department': '',
                     'affiliation': '',
                     'sponsor_type': ''
                 }},
            ]
            return study_associates

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        return StudyAssociatedSchema(many=True).dump(StudyService.get_study_associates(study_id))
