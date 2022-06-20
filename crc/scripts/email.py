import sys
import traceback

from crc import app, session
from crc.api.common import ApiError
from crc.models.email import EmailModel, EmailModelSchema
from crc.models.file import FileModel, CONTENT_TYPES
from crc.models.workflow import WorkflowModel
from crc.services.document_service import DocumentService
from crc.scripts.script import Script
from crc.services.email_service import EmailService
from crc.services.ldap_service import LdapService
from crc.services.study_service import StudyService

import datetime


class Email(Script):
    """Send an email from a script task, as part of a workflow.
       You must specify recipients and subject.
       You can also specify cc, bcc, reply_to, and attachments.
       The email content must be in the Element Documentation for the task."""

    def get_description(self):
        return """Creates an email, using the provided `subject` and `recipients` arguments, which are required.
The `Element Documentation` field in the script task must contain markdown that becomes the body of the email message.

You can also provide `cc`, `bcc`, `reply_to` and `attachments` arguments.  
The cc, bcc, reply_to, and attachments arguments are not required.

The recipients, cc, and bcc arguments can contain an email address or list of email addresses. 
In place of an email address, we accept the string 'associated', in which case we
look up the users associated with the study who have send_email set to True. 
The reply_to argument can contain an email address.

The attachments argument can contain a doc_code string, a doc_code tuple or list of doc_code strings and tuples.
A doc_code tuple contains a doc_code and list (of file_names).

Normally, we include *all* files for each doc_code. The optional list of file_names allows 
us to limit the files we include to only the files in the list. 

Examples:
email(subject="My Subject", recipients=["dhf8r@virginia.edu", pi.email, 'associated'])
email(subject="My Subject", recipients="user@example.com", cc='associated', bcc='test_user@example.com)
email(subject="My Subject", recipients="user@example.com", reply_to="reply_to@example.com")
email(subject="My Subject", recipients="user@example.com", attachments='Study_App_Doc')
email(subject="My Subject", recipients="user@example.com", attachments=['Study_App_Doc', Study_Protocol_Document])
email(subject="My Subject", recipients="user@example.com", attachments=('Study_App_Doc', []))
email(subject="My Subject", recipients="user@example.com", attachments=[('Study_App_Doc', ['some_file_name']),('Study_Protocol_Document',[])])
email(subject="My Subject", recipients="user@example.com", attachments=[('Study_App_Doc', ['some_file_name']), 'Study_Protocol_Document'])
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
            name = None
            if 'cc' in kwargs and kwargs['cc'] is not None:
                cc = self.get_email_addresses(kwargs['cc'], study_id)
            if 'bcc' in kwargs and kwargs['bcc'] is not None:
                bcc = self.get_email_addresses(kwargs['bcc'], study_id)
            if 'reply_to' in kwargs:
                reply_to = kwargs['reply_to']
            # Don't process if attachments is None or ''
            if 'attachments' in kwargs and kwargs['attachments'] is not None and kwargs['attachments'] != '':
                files = self.get_files(kwargs['attachments'], study_id)
            if 'name' in kwargs and kwargs['name'] is not None:
                name = kwargs['name']

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
                    workflow_spec_id=workflow_spec_id,
                    name=name
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

    def __process_attachments(self, attachments):
        """Return either a doc_code_tuple or a list of doc_code_tuples

           attachments can be a string, a tuple, or a list

           if attachments is a string, build a tuple with an empty list
           if attachments is a tuple, make sure it is a string and a list

           if attachments is a list, each of the items can be a string or a tuple
           process each of them accordingly"""

        doc_code_tuple = None
        return_list = None

        def is_filter_tuple(candidate):
            return len(candidate) == 2 and \
                   isinstance(candidate[0], str) and \
                   isinstance(candidate[1], list)

        # one doc_code, no filtering
        if isinstance(attachments, str):
            doc_code_tuple = (attachments, [])

        # if we have a doc_code and a filter list
        elif is_filter_tuple(attachments):
            doc_code_tuple = (attachments[0], attachments[1])

        elif isinstance(attachments, list):

            # if everything in the list is a string
            if all(isinstance(x, str) for x in attachments):
                return_list = [(doc_code, []) for doc_code in attachments]

            else:
                return_list = []
                for item in attachments:
                    attachment = self.process_attachments(item)
                    if len(attachment) == 2:
                        return_list.append(attachment)
                    else:
                        if len(attachment) == 1 and len(attachment[0]) == 2:
                            return_list.append((attachment[0]))
        return doc_code_tuple, return_list

    def process_attachments(self, attachments):
        """Return a list of tuples like [(doc_code, ['some_file']), (another_doc_code, [])]
           built from the attachments list"""

        doc_code_tuple, return_list = self.__process_attachments(attachments)

        # One of these should be None and the other should not
        if return_list is None and doc_code_tuple is not None:
            return [doc_code_tuple]
        if doc_code_tuple is None and return_list is not None:
            return return_list

    def get_files(self, attachments, study_id):
        attachments = self.process_attachments(attachments)
        files = []

        if attachments is not None:
            for attachment in attachments:
                doc_code = attachment[0]
                file_filter = attachment[1]
                if DocumentService.is_allowed_document(doc_code):
                    workflows = session.query(WorkflowModel).filter(WorkflowModel.study_id==study_id).all()
                    for workflow in workflows:

                        query = session.query(FileModel).\
                            filter(FileModel.workflow_id == workflow.id).\
                            filter(FileModel.irb_doc_code == doc_code)
                        if isinstance(file_filter, list) and len(file_filter) > 0:
                            query = query.filter(FileModel.name.in_(file_filter))

                        workflow_files = query.all()
                        for file in workflow_files:
                            files.append({'id': file.id,
                                          'name': file.name,
                                          'type': CONTENT_TYPES[file.type],
                                          'data': file.data,
                                          'doc_code': doc_code})
                else:
                    raise ApiError(code='bad_doc_code',
                                   message=f'The doc_code {doc_code} is not valid.')
        else:
            raise ApiError(code='bad_argument_type',
                           message='The attachments argument must be a string or list of strings')

        return files
