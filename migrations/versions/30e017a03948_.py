"""add user_uid column to file_data table

Revision ID: 30e017a03948
Revises: bbf064082623
Create Date: 2021-07-06 10:39:04.661704

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '30e017a03948'
down_revision = 'bbf064082623'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('file_data', sa.Column('user_uid', sa.String(), nullable=True))
    op.create_foreign_key(None, 'file_data', 'user', ['user_uid'], ['uid'])


def downgrade():
    # op.drop_constraint('file_data_user_uid_fkey', 'file_data', type_='foreignkey')
    # op.execute("update file_data set user_uid = NULL WHERE user_uid IS NOT NULL")
    op.drop_column('file_data', 'user_uid')
