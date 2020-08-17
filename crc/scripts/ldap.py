import copy

from flask import g

from crc import app
from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.ldap_service import LdapService
from crc.services.user_service import UserService


class Ldap(Script):
    """This Script allows to be introduced as part of a workflow and called from there, taking
    a UID (or several) as input and looking it up through LDAP to return the person's details.
    If no user id is specified, returns information about the current user."""

    def get_description(self):
        return """
Attempts to create a dictionary with person details, using the
provided argument (a UID) and look it up through LDAP.  If no UID is
provided, then returns information about the current user.

Examples:
supervisor_info = ldap(supervisor_uid)   // Sets the supervisor information to ldap details for the given uid.
"""

    def do_task_validate_only(self, task, *args, **kwargs):
        return self.set_users_info_in_task(task, args)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        return self.set_users_info_in_task(task, args)

    def set_users_info_in_task(self, task, args):
        if len(args) > 1:
            raise ApiError(code="invalid_argument",
                           message="Ldap takes at most one argument, the "
                                   "UID for the person we want to look up.")
        if len(args) < 1:
            if UserService.has_user():
               uid = UserService.current_user().uid
        else:
            uid = args[0]
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
