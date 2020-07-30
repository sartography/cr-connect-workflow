import copy

from crc import app
from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.ldap_service import LdapService


USER_DETAILS = {
    "PIComputingID": {
        "value": "",
        "data": {
         },
        "label": "invalid uid"
    }
}


class LdapLookup(Script):
    """This Script allows to be introduced as part of a workflow and called from there, taking
    a UID as input and looking it up through LDAP to return the person's details """

    def get_description(self):
        return """
Attempts to create a dictionary with person details, using the
provided argument (a UID) and look it up through LDAP.

Example:
LdapLookup PIComputingID
"""

    def do_task_validate_only(self, task, *args, **kwargs):
        self.get_user_info(task, args)

    def do_task(self, task, *args, **kwargs):
        args = [arg for arg in args if type(arg) == str]
        user_info = self.get_user_info(task, args)

        user_details = copy.deepcopy(USER_DETAILS)
        user_details['PIComputingID']['value'] = user_info['uid']
        if len(user_info.keys()) > 1:
            user_details['PIComputingID']['label'] = user_info.pop('label')
        else:
            user_info.pop('uid')
        user_details['PIComputingID']['data'] = user_info
        return user_details

    def get_user_info(self, task, args):
        if len(args) < 1:
            raise ApiError(code="missing_argument",
                           message="Ldap lookup script requires one argument. The "
                                   "UID for the person we want to look up")

        arg = args.pop()  # Extracting only one value for now
        uid = task.workflow.script_engine.evaluate_expression(task, arg)
        if not isinstance(uid, str):
            raise ApiError(code="invalid_argument",
                           message="Ldap lookup script requires one 1 UID argument, of type string.")
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
                "label": user_info.proper_name()
            }
        except:
            user_info_dict['uid'] = uid
            app.logger.error(f'Ldap lookup failed for UID {uid}')

        return user_info_dict
