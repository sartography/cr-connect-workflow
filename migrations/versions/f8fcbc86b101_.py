"""empty message

Revision ID: f8fcbc86b101
Revises: 3d9ae7cfc231
Create Date: 2021-07-23 11:23:17.269985

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f8fcbc86b101'
down_revision = '3d9ae7cfc231'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('data_store', sa.Column('task_spec', sa.String(), nullable=True))
    op.drop_column('data_store', 'task_id')
    op.add_column('file', sa.Column('task_spec', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('file', 'task_spec')
    op.add_column('data_store', sa.Column('task_id', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('data_store', 'task_spec')
    # ### end Alembic commands ###
