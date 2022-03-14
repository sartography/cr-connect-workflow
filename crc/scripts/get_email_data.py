from SpiffWorkflow.exceptions import WorkflowTaskExecException

from crc.scripts.script import Script
from crc.api.common import ApiError
from crc import session
from crc.models.email import EmailModel, EmailModelSchema
from crc.services.email_service import EmailService

import datetime


class EmailData(Script):

    def get_description(self):
        return """This is my description"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if 'email_id' in kwargs or 'workflow_spec_id' in kwargs:
            subject = 'My Test Email'
            recipients = 'user@example.com'
            content = "Hello"
            content_html = "<!DOCTYPE html><html><head></head><body><div><h2>Hello</h2></div></body></html>"
            email_model = EmailModel(subject=subject,
                                     recipients=recipients,
                                     content=content,
                                     content_html=content_html,
                                     timestamp=datetime.datetime.utcnow())
            return EmailModelSchema(many=True).dump([email_model])

        else:
            raise WorkflowTaskExecException(task, f'get_email_data() failed. You must include an email_id or '
                                                  f'workflow_spec_id with the get_email_data script.')

    def do_task(self, task, study_id, workflow_id, *args, **kwargs):
        email_models = None
        email_data = None
        if 'email_id' in kwargs:
            email_models = session.query(EmailModel).filter(EmailModel.id == kwargs['email_id']).all()
        elif 'workflow_spec_id' in kwargs:
            email_models = session.query(EmailModel)\
                .filter(EmailModel.study_id == study_id)\
                .filter(EmailModel.workflow_spec_id == str(kwargs['workflow_spec_id']))\
                .all()
        else:
            raise WorkflowTaskExecException(task, f'get_email_data() failed. You must include an email_id or '
                                                  f'workflow_spec_id with the get_email_data script.')

        if email_models:
            email_data = EmailModelSchema(many=True).dump(email_models)
        return email_data
