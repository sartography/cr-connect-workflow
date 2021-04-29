"""empty message

Revision ID: 8b976945a54e
Revises: c872232ebdcb
Create Date: 2021-04-18 11:42:41.894378

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8b976945a54e'
down_revision = 'c872232ebdcb'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('workflow', sa.Column('user_id', sa.String(), nullable=True))
    op.add_column('workflow_spec', sa.Column('standalone', sa.Boolean(), default=False))
    op.execute("UPDATE workflow_spec SET standalone=False WHERE standalone is null;")
    op.execute("ALTER TABLE task_event ALTER COLUMN study_id DROP NOT NULL")


def downgrade():
    op.execute("UPDATE workflow SET user_id=NULL WHERE user_id is not NULL")
    op.drop_column('workflow', 'user_id')
    op.drop_column('workflow_spec', 'standalone')
    op.execute("ALTER TABLE task_event ALTER COLUMN study_id SET NOT NULL ")
