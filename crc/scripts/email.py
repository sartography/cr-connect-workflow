import re

import markdown
from jinja2 import Template

from crc import app
from crc.api.common import ApiError
from crc.models.user import UserModel
from crc.scripts.script import Script
from crc.services.ldap_service import LdapService
from crc.services.email_service import EmailService
from crc.services.study_service import StudyService

from flask import render_template, request


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

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.get_subject(kwargs['subject'])
        self.get_email_recipients(kwargs['recipients'])
        self.get_content(task)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        if 'subject' in kwargs and 'recipients' in kwargs:
            subject = self.get_subject(kwargs['subject'])

            # we can send the email to all the people associated with a study
            # who have send_email set to True
            if kwargs['recipients'] == 'associated':
                recipient_uids = []
                recipients = []
                associates = StudyService.get_study_associates(study_id)
                for associate in associates:
                    if associate['send_email'] is True:
                        recipient_uids.append(associate['uid'])
                        # Shoe.query.filter(Shoe.id.in_(my_list_of_ids)).all()
                returned = UserModel.query.filter(UserModel.uid.in_(recipient_uids)).all()
                for item in returned:
                    recipients.append(item.email_address)
            else:
                recipients = self.get_email_recipients(kwargs['recipients'])

        else:
            raise ApiError(code="missing_argument",
                           message="Email script requires a subject and at least one email address as arguments")

        if recipients:
            content, content_html = self.get_content(task)
            EmailService.add_email(
                subject=subject,
                sender=app.config['DEFAULT_SENDER'],
                recipients=recipients,
                content=content,
                content_html=content_html,
                study_id=study_id
            )

    @staticmethod
    def check_valid_email(email):
        # regex from https://emailregex.com/
        regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        if re.search(regex, email):
            return True
        else:
            return False

    def get_email_recipients(self, recipients):
        emails = []

        # Recipient can be an email address or list of email addresses
        if isinstance(recipients, str):
            emails_to_check = [recipients]
        elif isinstance(recipients, list):
            emails_to_check = recipients
        else:
            raise ApiError(code="invalid_argument",
                           message=f"Email script requires a valid email address (or list of addresses), but received '{recipients}'")

        for e in emails_to_check:
            if self.check_valid_email(e):
                emails.append(e)
            else:
                raise ApiError(code="invalid_argument",
                               message="The email address you provided could not be parsed. "
                                       "The value you provided is '%s" % e)

        return emails

    @staticmethod
    def get_subject(subject):
        if not subject or not isinstance(subject, str):
            raise ApiError(code="invalid_argument",
                           message="The subject you provided could not be parsed. "
                               "The value is \"%s\" " % subject)

        return subject

    def get_content(self, task):
        content = task.task_spec.documentation
        template = Template(content)
        rendered = template.render(task.data)
        rendered_markdown = markdown.markdown(rendered)
        wrapped = self.get_cr_connect_wrapper(rendered_markdown)

        return rendered, wrapped

    @staticmethod
    def get_cr_connect_wrapper(email_body):
        return render_template('mail_content_template.html', email_body=email_body, base_url=request.base_url)
