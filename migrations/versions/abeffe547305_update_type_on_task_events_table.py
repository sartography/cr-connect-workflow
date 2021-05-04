"""update type on task_events table and workflow table

Revision ID: abeffe547305
Revises: 665624ac29f1
Create Date: 2021-04-28 08:51:16.220260

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abeffe547305'
down_revision = '665624ac29f1'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("alter table task_event alter column date type timestamp with time zone")
    op.execute("alter table workflow alter column last_updated type timestamp with time zone")
    pass


def downgrade():
    op.execute("alter table task_event alter column date type timestamp without time zone")
    op.execute("alter table workflow alter column last_updated type timestamp without time zone")
    pass
