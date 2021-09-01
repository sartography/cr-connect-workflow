"""Delete file stuff - add task_spec to file and data_store

Revision ID: 981156283cb9
Revises: 3d9ae7cfc231
Create Date: 2021-08-26 09:51:58.422819

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '981156283cb9'
down_revision = '3d9ae7cfc231'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('data_store', sa.Column('task_spec', sa.String(), nullable=True))
    op.drop_column('data_store', 'task_id')
    op.add_column('file', sa.Column('task_spec', sa.String(), nullable=True))


def downgrade():
    op.drop_column('file', 'task_spec')
    op.add_column('data_store', sa.Column('task_id', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('data_store', 'task_spec')
