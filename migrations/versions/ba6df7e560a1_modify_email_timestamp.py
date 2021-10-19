"""modify email timestamp

Revision ID: ba6df7e560a1
Revises: 6d8ceb1c18cb
Create Date: 2021-10-13 10:54:23.894034

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ba6df7e560a1'
down_revision = '6d8ceb1c18cb'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("alter table email alter column timestamp type timestamp with time zone")


def downgrade():
    op.execute("alter table email alter column timestamp type timestamp without time zone")
