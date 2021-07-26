import sys
import traceback

from crc import app
from crc.api.common import ApiError
from crc.scripts.script import Script
from crc.services.ldap_service import LdapService
from crc.services.email_service import EmailService
from crc.services.study_service import StudyService


class Email(Script):
    """This Script allows to be introduced as part of a workflow and called from there, specifying
    recipients and content """

    def get_description(self):
        return """
Creates an email, using the provided `subject`, `recipients`, and `cc` arguments.  
The recipients and cc arguments can contain an email address or list of email addresses. 
In place of an email address, we accept the string 'associated', in which case we
look up the users associated with the study who have send_email set to True. 
The cc argument is not required.
The "documentation" should contain markdown that will become the body of the email message.
Examples:
email (subject="My Subject", recipients=["dhf8r@virginia.edu", pi.email, 'associated'])
email (subject="My Subject", recipients=["dhf8r@virginia.edu", pi.email], cc='associated')
"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        self.get_subject(kwargs['subject'])
        self.get_email_addresses(kwargs['recipients'], study_id)
        EmailService().get_rendered_content(task.task_spec.documentation, task.data)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        if 'subject' in kwargs and 'recipients' in kwargs:
            subject = self.get_subject(kwargs['subject'])
            recipients = self.get_email_addresses(kwargs['recipients'], study_id)
            cc = []
            if 'cc' in kwargs and kwargs['cc'] is not None:
                cc = self.get_email_addresses(kwargs['cc'], study_id)

        else:
            raise ApiError(code="missing_argument",
                           message="Email script requires a subject and at least one email recipient as arguments")

        if recipients:
            message = task.task_spec.documentation
            data = task.data
            try:
                content, content_html = EmailService().get_rendered_content(message, data)
                EmailService.add_email(
                    subject=subject,
                    sender=app.config['DEFAULT_SENDER'],
                    recipients=recipients,
                    content=content,
                    content_html=content_html,
                    cc=cc,
                    study_id=study_id
                )
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print("*** format_exception:")
                # exc_type below is ignored on 3.5 and later
                print(repr(traceback.format_exception(exc_type, exc_value,
                                                      exc_traceback)))
                raise e

    def get_email_addresses(self, users, study_id):
        emails = []
        emails_to_check = []

        # Recipient can be an email address or list of email addresses
        # We also accept the string 'associated', in which case we lookup
        # all users associated with a study who have send_email set to True
        if isinstance(users, str):
            if users == 'associated':
                associated_emails = self.get_associated_emails(study_id)
                for email in associated_emails:
                    emails_to_check.append(email)
            else:
                emails_to_check.append(users)
        elif isinstance(users, list):
            for user in users:
                if user == 'associated':
                    associated_emails = self.get_associated_emails(study_id)
                    for email in associated_emails:
                        emails_to_check.append(email)
                else:
                    emails_to_check.append(user)
        else:
            raise ApiError(code="invalid_argument",
                           message=f"Email script requires a valid email address (or list of addresses), but we received '{users}'")

        for e in emails_to_check:
            if EmailService().check_valid_email(e):
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

    @staticmethod
    def get_associated_emails(study_id):
        associated_emails = []
        associates = StudyService.get_study_associates(study_id)
        for associate in associates:
            if associate['send_email'] is True:
                user_info = LdapService.user_info(associate['uid'])
                associated_emails.append(user_info.email_address)
        return associated_emails
