import markdown
import re

from flask import render_template
from flask_mail import Message
from jinja2 import Template

from crc import app, db, mail, session

from crc.models.email import EmailModel
from crc.models.file import FileDataModel
from crc.models.study import StudyModel

from crc.services.jinja_service import JinjaService


class EmailService(object):
    """Provides common tools for working with an Email"""

    @staticmethod
    def add_email(subject, sender, recipients, content, content_html,
                  cc=None, bcc=None, study_id=None, reply_to=None, attachment_files=None, workflow_spec_id=None):
        """We will receive all data related to an email and store it"""

        # Find corresponding study - if any
        study = None
        if type(study_id) == int:
            study = db.session.query(StudyModel).get(study_id)

        # Create EmailModel
        email_model = EmailModel(subject=subject, sender=sender, recipients=str(recipients),
                                 content=content, content_html=content_html, study=study,
                                 cc=cc, bcc=bcc, workflow_spec_id=workflow_spec_id)

        # Send mail
        try:
            msg = Message(subject,
                          sender=sender,
                          recipients=recipients,
                          body=content,
                          html=content_html,
                          cc=cc,
                          bcc=bcc,
                          reply_to=reply_to)

            if attachment_files is not None:
                for file in attachment_files:
                    file_data = session.query(FileDataModel).filter(FileDataModel.file_model_id==file['id']).first()
                    msg.attach(file['name'], file['type'], file_data.data)

            mail.send(msg)

        except Exception as e:
            app.logger.error('An exception happened in EmailService', exc_info=True)
            app.logger.error(str(e))
            raise e

        db.session.add(email_model)
        db.session.commit()
        return email_model

    @staticmethod
    def check_valid_email(email):
        # regex from https://emailregex.com/
        regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        if re.search(regex, email):
            return True
        else:
            return False

    def get_rendered_content(self, message, data):
        content = JinjaService.get_content(message, data)
        rendered_markdown = markdown.markdown(content, extensions=['nl2br'])
        content_html = self.get_cr_connect_wrapper(rendered_markdown)

        return content, content_html

    @staticmethod
    def get_cr_connect_wrapper(email_body):
        base_url = app.config['FRONTEND']  # The frontend url
        return render_template('mail_content_template.html', email_body=email_body, base_url=base_url)
