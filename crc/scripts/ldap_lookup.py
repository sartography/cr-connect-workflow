import copy

from crc import app
from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.ldap_service import LdapService


class LdapReplace(Script):
    """This Script allows to be introduced as part of a workflow and called from there, taking
    a UID (or several) as input and looking it up through LDAP to return the person's details """

    def get_description(self):
        return """
Attempts to create a dictionary with person details, using the
provided argument (a UID) and look it up through LDAP.

Examples:
#! LdapReplace supervisor
#! LdapReplace supervisor collaborator
#! LdapReplace supervisor cosupervisor collaborator
"""

    def do_task_validate_only(self, task, *args, **kwargs):
        self.set_users_info_in_task(task, args)

    def do_task(self, task, *args, **kwargs):
        args = [arg for arg in args if type(arg) == str]
        self.set_users_info_in_task(task, args)

    def set_users_info_in_task(self, task, args):
        if len(args) < 1:
            raise ApiError(code="missing_argument",
                           message="Ldap replace script requires at least one argument. The "
                                   "UID for the person(s) we want to look up")

        users_info = {}
        for arg in args:
            uid = task.workflow.script_engine.evaluate_expression(task, arg)
            if not isinstance(uid, str):
                raise ApiError(code="invalid_argument",
                               message="Ldap replace script found an invalid argument, type string is required")
            user_info_dict = {}
            try:
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
            except:
                app.logger.error(f'Ldap replace failed for UID {uid}')
            task.data[arg] = user_info_dict
