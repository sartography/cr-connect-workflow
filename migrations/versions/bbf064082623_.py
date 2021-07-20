"""empty message

Revision ID: bbf064082623
Revises: c1449d1d1681
Create Date: 2021-05-13 15:07:44.463757

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy import func

revision = 'bbf064082623'
down_revision = 'c1449d1d1681'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('data_store', 'last_updated', server_default=func.now())
    op.alter_column('file_data', 'date_created', server_default=func.now())
    op.alter_column('data_store', 'last_updated', server_default=func.now())
    op.alter_column('ldap_model', 'date_cached', server_default=func.now())
    op.alter_column('study', 'last_updated', server_default=func.now())
    op.alter_column('study_event', 'create_date', server_default=func.now())
    op.alter_column('workflow', 'last_updated', server_default=func.now())


def downgrade():
    op.alter_column('data_store', 'last_updated', server_default=None)
    op.alter_column('file_data', 'date_created', server_default=None)
    op.alter_column('data_store', 'last_updated', server_default=None)
    op.alter_column('ldap_model', 'date_cached', server_default=None)
    op.alter_column('study', 'last_updated', server_default=None)
    op.alter_column('study_event', 'create_date', server_default=None)
    op.alter_column('workflow', 'last_updated', server_default=None)
