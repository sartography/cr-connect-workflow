import markdown
import re

from datetime import datetime
from flask import render_template, request
from flask_mail import Message
from jinja2 import Template
from sqlalchemy import desc

from crc import app, db, mail, session
from crc.api.common import ApiError

from crc.models.study import StudyModel
from crc.models.email import EmailModel



class EmailService(object):
    """Provides common tools for working with an Email"""

    @staticmethod
    def add_email(subject, sender, recipients, content, content_html, cc=None, study_id=None):
        """We will receive all data related to an email and store it"""

        # Find corresponding study - if any
        study = None
        if type(study_id) == int:
            study = db.session.query(StudyModel).get(study_id)

        # Create EmailModel
        email_model = EmailModel(subject=subject, sender=sender, recipients=str(recipients),
                                 content=content, content_html=content_html, study=study)

        # Send mail
        try:
            msg = Message(subject,
                          sender=sender,
                          recipients=recipients)

            msg.body = content
            msg.html = content_html
            msg.cc = cc

            mail.send(msg)
        except Exception as e:
            app.logger.error('An exception happened in EmailService', exc_info=True)
            app.logger.error(str(e))

        db.session.add(email_model)
        db.session.commit()

    @staticmethod
    def check_valid_email(email):
        # regex from https://emailregex.com/
        regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
        if re.search(regex, email):
            return True
        else:
            return False

    def get_rendered_content(self, message, data):
        template = Template(message)
        rendered = template.render(data)
        rendered_markdown = markdown.markdown(rendered)
        wrapped = self.get_cr_connect_wrapper(rendered_markdown)

        return rendered, wrapped

    @staticmethod
    def get_cr_connect_wrapper(email_body):
        return render_template('mail_content_template.html', email_body=email_body, base_url=request.base_url)
