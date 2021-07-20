"""change irb_documents to documents

Revision ID: c16d3047abbe
Revises: bbf064082623
Create Date: 2021-07-07 13:07:53.966102

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c16d3047abbe'
down_revision = 'bbf064082623'
branch_labels = None
depends_on = None


def upgrade():
    pass
    op.execute("update file set name = 'documents.xlsx' where name='irb_documents.xlsx'")


def downgrade():
    op.execute("update file set name = 'irb_documents.xlsx' where name='documents.xlsx'")
