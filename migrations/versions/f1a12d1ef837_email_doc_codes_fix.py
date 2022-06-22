"""email-doc-codes-fix

Revision ID: f1a12d1ef837
Revises: a323a4d14bd7
Create Date: 2022-06-22 14:51:39.892773

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1a12d1ef837'
down_revision = 'a323a4d14bd7'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE email_doc_codes RENAME COLUMN doc_codes TO doc_code;")


def downgrade():
    op.execute("ALTER TABLE email_doc_codes RENAME COLUMN doc_code TO doc_codes;")
