from datetime import datetime

from sqlalchemy import desc

from crc import app, db, session
from crc.api.common import ApiError

from crc.models.study import StudyModel
from crc.models.email import EmailModel


class EmailService(object):
    """Provides common tools for working with an Email"""

    @staticmethod
    def add_email(subject, sender, recipients, content, content_html, study_id):
        """We will receive all data related to an email and store it"""

        # Find corresponding study - if any
        study = None
        if type(study_id) == int:
            study = db.session.query(StudyModel).get(study_id)

        # Create EmailModel
        email_model = EmailModel(subject=subject, sender=sender, recipients=str(recipients),
                                 content=content, content_html=content_html, study=study)

        # TODO: Send email from here, not from caller functions

        db.session.add(email_model)
        db.session.commit()
