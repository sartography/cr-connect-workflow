import re

import markdown
from jinja2 import Template

from crc import app
from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.ldap_service import LdapService
from crc.services.mails import send_mail


class Email(Script):
    """This Script allows to be introduced as part of a workflow and called from there, specifying
    recipients and content """

    def get_description(self):
        return """
Creates an email, using the provided arguments (a list of UIDs)"
Each argument will be used to look up personal information needed for
the email creation.

Example:
Email Subject ApprvlApprvr1 PIComputingID
"""

    def do_task_validate_only(self, task, *args, **kwargs):
        self.get_subject(task, args)
        self.get_email_recipients(task, args)
        self.get_content(task)

    def do_task(self, task, *args, **kwargs):
        args = [arg for arg in args if type(arg) == str or type(arg) == list]

        subject = args[0]
        recipients = None
        try:
            recipients = self.get_email_recipients(task, args)
        except ApiError:
            raise
        content, content_html = self.get_content(task)
        if recipients:
            send_mail(
                subject=subject,
                sender=app.config['DEFAULT_SENDER'],
                recipients=recipients,
                content=content,
                content_html=content_html
            )

    def check_valid_email(self, email):
        # regex from https://emailregex.com/
        regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        if (re.search(regex, email)):
            return True
        else:
            return False

    def get_email_recipients(self, task, args):
        emails = []

        if len(args[1]) < 1:
            raise ApiError(code="missing_argument",
                           message="Email script requires at least one email address as an argument. "
                                   "Multiple email addresses are accepted.")

        if isinstance(args[1], str):
            if self.check_valid_email(args[1]):
                emails.append(args[1])
            else:
                raise ApiError(code="invalid_argument",
                               message="The email address you provided could not be parsed. "
                                       "The value you provided is '%s" % args[1])

        if isinstance(args[1], list):
            for address in args[1]:
                if self.check_valid_email(address):
                    emails.append(address)
                else:
                    raise ApiError(code="invalid_argument",
                                   message="The email address you provided could not be parsed. "
                                           "The value you provided is '%s" % address)

        if len(emails) > 0:
            return emails
        else:
            raise ApiError(code="invalid_argument",
                           message="Email script requires a valid email address.")

    # def get_users_info(self, task, args):
    #     if len(args) < 1:
    #         raise ApiError(code="missing_argument",
    #                        message="Email script requires at least one argument.  The "
    #                                "name of the variable in the task data that contains user"
    #                                "id to process.  Multiple arguments are accepted.")
    #     emails = []
    #     for arg in args:
    #         try:
    #             uid = task.workflow.script_engine.evaluate_expression(task, arg)
    #         except Exception as e:
    #             app.logger.error(f'Workflow engines could not parse {arg}', exc_info=True)
    #             continue
    #         user_info = LdapService.user_info(uid)
    #         email = user_info.email_address
    #         emails.append(user_info.email_address)
    #         if not isinstance(email, str):
    #             raise ApiError(code="invalid_argument",
    #                            message="The Email script requires at least 1 UID argument.  The "
    #                                "name of the variable in the task data that contains subject and"
    #                                " user ids to process.  This must point to an array or a string, but "
    #                                "it currently points to a %s " % emails.__class__.__name__)
    #
    #     return emails

    def get_subject(self, task, args):
        # subject = ''
        if len(args[0]) < 1:
            raise ApiError(code="missing_argument",
                           message="No subject was provided for the email message.")

        subject = args[0]
        if not subject or not isinstance(subject, str):
            raise ApiError(code="invalid_argument",
                           message="The subject you provided could not be parsed. "
                               "The value is \"%s\" " % subject)

        return subject

    def get_content(self, task):
        content = task.task_spec.documentation
        template = Template(content)
        rendered = template.render(task.data)
        rendered_markdown = markdown.markdown(rendered).replace('\n', '<br>')
        return rendered, rendered_markdown
