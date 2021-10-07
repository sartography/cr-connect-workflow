from crc.scripts.script import Script
from crc.api.common import ApiError
from crc import session
from crc.models.email import EmailModel, EmailModelSchema
import json


class EmailData(Script):

    def get_description(self):
        return """This is my description"""

    def do_task_validate_only(self, task, study_id, workflow_id, *args, **kwargs):
        if 'email_id' in kwargs or 'workflow_id' in kwargs:
            return True
        else:
            return False

    def do_task(self, task, study_id, workflow_id, **kwargs):
        email_models = None
        email_data = None
        if 'email_id' in kwargs:
            email_models = session.query(EmailModel).filter(EmailModel.id == kwargs['email_id']).all()
        elif 'email_workflow_id' in kwargs:
            email_models = session.query(EmailModel).filter(EmailModel.workflow_id == str(kwargs['email_workflow_id'])).all()
        else:
            raise ApiError.from_task(code='missing_email_id',
                                     message='You must include an email_id with the get_email_data script.',
                                     task=task)

        if email_models:
            email_data = EmailModelSchema(many=True).dump(email_models)
        return email_data
