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
        self.get_users_info(task, args)
        self.get_content(task, {})

    def do_task(self, task, *args, **kwargs):
        subject = self.get_subject(task, args)
        recipients, display_keys = self.get_users_info(task, args)
        content, content_html = self.get_content(task, display_keys)
        if recipients:
            send_mail(
                subject=subject,
                sender=app.config['DEFAULT_SENDER'],
                recipients=recipients,
                content=content,
                content_html=content_html
            )

    def get_users_info(self, task, args):
        if len(args) < 1:
            raise ApiError(code="missing_argument",
                           message="Email script requires at least one argument.  The "
                                   "name of the variable in the task data that contains user"
                                   "id to process.  Multiple arguments are accepted.")
        emails = []
        display_keys = {}
        for arg in args[1:]:
            uid = task.workflow.script_engine.evaluate_expression(task, arg)
            user_info = LdapService.user_info(uid)
            email = user_info.email_address
            emails.append(user_info.email_address)
            display_keys[arg] = user_info.proper_name()
            if not isinstance(email, str):
                raise ApiError(code="invalid_argument",
                               message="The Email script requires at least 1 UID argument.  The "
                                   "name of the variable in the task data that contains subject and"
                                   " user ids to process.  This must point to an array or a string, but "
                                   "it currently points to a %s " % emails.__class__.__name__)

        return emails, display_keys

    def get_subject(self, task, args):
        if len(args) < 1:
            raise ApiError(code="missing_argument",
                           message="Email script requires at least one subject argument.  The "
                                   "name of the variable in the task data that contains subject"
                                   " to process. Multiple arguments are accepted.")
        subject = task.workflow.script_engine.evaluate_expression(task, args[0])
        if not isinstance(subject, str):
                raise ApiError(code="invalid_argument",
                               message="The Email script requires 1 argument.  The "
                                   "the name of the variable in the task data that contains user"
                                   "ids to process.  This must point to an array or a string, but "
                                   "it currently points to a %s " % subject.__class__.__name__)

        return subject

    def get_content(self, task, display_keys):
        content = task.task_spec.documentation
        template = Template(content)
        rendered = template.render(display_keys)
        rendered_markdown = markdown.markdown(rendered).replace('\n', '<br>')
        return rendered, rendered_markdown
