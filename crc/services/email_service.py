from datetime import datetime

from sqlalchemy import desc

from crc import app, db, session
from crc.api.common import ApiError

from crc.models.approval import ApprovalModel
from crc.models.email import EmailModel


class EmailService(object):
    """Provides common tools for working with an Email"""

    @staticmethod
    def add_email(subject, sender, recipients, content, content_html, approval_id):
        """We will receive all data related to an email and store it"""

        # Find corresponding approval
        approval = db.session.query(ApprovalModel).get(approval_id)

        # Create EmailModel
        email_model = EmailModel(subject=subject, sender=sender, recipients=str(recipients),
                                 content=content, content_html=content_html, approval=approval)

        db.session.add(email_model)
        db.session.commit()
