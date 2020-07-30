import copy

from crc import app
from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.ldap_service import LdapService


class Ldap(Script):
    """This Script allows to be introduced as part of a workflow and called from there, taking
    a UID (or several) as input and looking it up through LDAP to return the person's details """

    def get_description(self):
        return """
Attempts to create a dictionary with person details, using the
provided argument (a UID) and look it up through LDAP.

Examples:
supervisor_info = ldap(supervisor_uid)   // Sets the supervisor information to ldap details for the given uid.
"""

    def do_task_validate_only(self, task, *args, **kwargs):
        return self.set_users_info_in_task(task, args)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        return self.set_users_info_in_task(task, args)

    def set_users_info_in_task(self, task, args):
        if len(args) != 1:
            raise ApiError(code="missing_argument",
                           message="Ldap takes a single argument, the "
                                   "UID for the person we want to look up")
        uid = args[0]
        user_info_dict = {}

        user_info = LdapService.user_info(uid)
        user_info_dict = {
            "display_name": user_info.display_name,
            "given_name": user_info.given_name,
            "email_address": user_info.email_address,
            "telephone_number": user_info.telephone_number,
            "title": user_info.title,
            "department": user_info.department,
            "affiliation": user_info.affiliation,
            "sponsor_type": user_info.sponsor_type,
            "uid": user_info.uid,
            "proper_name": user_info.proper_name()
        }

        return user_info_dict
