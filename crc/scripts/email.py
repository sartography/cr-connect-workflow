import sys
import traceback
import datetime

from crc import app, session
from crc.api.common import ApiError
from crc.models.email import EmailModel, EmailModelSchema
from crc.models.file import DocumentModel, CONTENT_TYPES
from crc.models.workflow import WorkflowModel
from crc.services.document_service import DocumentService
from crc.scripts.script import Script
from crc.services.email_service import EmailService
from crc.services.ldap_service import LdapService
from crc.services.study_service import StudyService

import datetime


class Email(Script):
    """Send an email from a script task, as part of a workflow.
       You must specify recipients and content.
       You can also specify cc, bcc, reply_to, and attachments"""

    def get_description(self):
        return """Creates an email, using the provided `subject` and `recipients` arguments, which are required.
The `Element Documentation` field in the script task must contain markdown that becomes the body of the email message.

You can also provide `cc`, `bcc`, `reply_to` and `attachments` arguments.  
The cc, bcc, reply_to, and attachments arguments are not required.

The recipients, cc, and bcc arguments can contain an email address or list of email addresses. 
In place of an email address, we accept the string 'associated', in which case we
look up the users associated with the study who have send_email set to True. 
The reply_to argument can contain an email address.
The attachments arguments can contain a doc_code or list of doc_codes.

Examples:
email(subject="My Subject", recipients=["dhf8r@virginia.edu", pi.email, 'associated'])
email(subject="My Subject", recipients="user@example.com", cc='associated', bcc='test_user@example.com)
email(subject="My Subject", recipients="user@example.com", reply_to="reply_to@example.com")
email(subject="My Subject", recipients="user@example.com", attachments='Study_App_Doc')
email(subject="My Subject", recipients="user@example.com", attachments=['Study_App_Doc','Study_Protocol_Document'])
"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        subject = self.get_subject(kwargs['subject'])
        recipients = self.get_email_addresses(kwargs['recipients'], study_id)
        content, content_html = EmailService().get_rendered_content(task.task_spec.documentation, task.data)
        email_model = EmailModel(id=1,
                                 subject=subject,
                                 recipients=recipients,
                                 content=content,
                                 content_html=content_html,
                                 timestamp=datetime.datetime.utcnow())
        return EmailModelSchema().dump(email_model)

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):

        if 'subject' in kwargs and 'recipients' in kwargs:
            subject = self.get_subject(kwargs['subject'])
            recipients = self.get_email_addresses(kwargs['recipients'], study_id)
            cc = []
            bcc = []
            reply_to = None
            files = None
            if 'cc' in kwargs and kwargs['cc'] is not None:
                cc = self.get_email_addresses(kwargs['cc'], study_id)
            if 'bcc' in kwargs and kwargs['bcc'] is not None:
                bcc = self.get_email_addresses(kwargs['bcc'], study_id)
            if 'reply_to' in kwargs:
                reply_to = kwargs['reply_to']
            # Don't process if attachments is None or ''
            if 'attachments' in kwargs and kwargs['attachments'] is not None and kwargs['attachments'] != '':
                files = self.get_files(kwargs['attachments'], study_id)

        else:
            raise ApiError(code="missing_argument",
                           message="Email script requires a subject and at least one email recipient as arguments")

        if recipients:
            wf_model = session.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
            workflow_spec_id = wf_model.workflow_spec_id
            message = task.task_spec.documentation
            data = task.data
            try:
                content, content_html = EmailService().get_rendered_content(message, data)
                email_model = EmailService.add_email(
                    subject=subject,
                    sender=app.config['DEFAULT_SENDER'],
                    recipients=recipients,
                    content=content,
                    content_html=content_html,
                    cc=cc,
                    bcc=bcc,
                    study_id=study_id,
                    reply_to=reply_to,
                    attachment_files=files,
                    workflow_spec_id=workflow_spec_id
                )
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                print("*** format_exception:")
                # exc_type below is ignored on 3.5 and later
                print(repr(traceback.format_exception(exc_type, exc_value,
                                                      exc_traceback)))
                raise e
            return EmailModelSchema().dump(email_model)

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
            if associate.send_email is True:
                user_info = LdapService.user_info(associate.uid)
                associated_emails.append(user_info.email_address)
        return associated_emails

    @staticmethod
    def get_files(attachments, study_id):
        files = []
        codes = None
        if isinstance(attachments, str):
            codes = [attachments]
        elif isinstance(attachments, list):
            codes = attachments

        if codes is not None:
            for code in codes:
                if DocumentService.is_allowed_document(code):
                    workflows = session.query(WorkflowModel).filter(WorkflowModel.study_id==study_id).all()
                    for workflow in workflows:
                        workflow_files = session.query(DocumentModel).\
                            filter(DocumentModel.workflow_id == workflow.id).\
                            filter(DocumentModel.irb_doc_code == code).all()
                        for file in workflow_files:
                            files.append({'id': file.id,
                                          'name': file.name,
                                          'type': CONTENT_TYPES[file.type],
                                          'data': file.data})
                else:
                    raise ApiError(code='bad_doc_code',
                                   message=f'The doc_code {code} is not valid.')
        else:
            raise ApiError(code='bad_argument_type',
                           message='The attachments argument must be a string or list of strings')

        return files
