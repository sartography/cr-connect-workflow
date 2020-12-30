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
Creates an email, using the provided arguments.  The first argument is the subject of the email, 
all subsequent arguments should be email addresses in quotes, or variables containing an email address or a list
of email addresses."
The "documentation" should contain markdown that will become the body of the email message.
Example:
email ("My Subject", "dhf8r@virginia.edu", pi.email)
"""

    def do_task_validate_only(self, task, *args, **kwargs):
        self.get_subject(task, args)
        self.get_email_recipients(task, args)
        self.get_content(task)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        if len(args) < 1:
            raise ApiError(code="missing_argument",
                           message="Email script requires a subject and at least one email address as arguments")
        subject = args[0]
        recipients = self.get_email_recipients(task, args)
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

        if len(args) < 2:
            raise ApiError(code="missing_argument",
                           message="Email script requires at least one email address as an argument. "
                                   "Multiple email addresses are accepted.")

        # Every argument following the subject should be an email, or a list of emails.
        for arg in args[1:]:
            if isinstance(arg, str):
                emails_to_check = [arg]
            elif isinstance(arg, list):
                emails_to_check = arg
            else:
                raise ApiError(code="invalid_argument",
                               message=f"Email script requires a valid email address, but received '{arg}'")

            for e in emails_to_check:
                if self.check_valid_email(e):
                    emails.append(e)
                else:
                    raise ApiError(code="invalid_argument",
                                   message="The email address you provided could not be parsed. "
                                           "The value you provided is '%s" % e)

        return emails

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
