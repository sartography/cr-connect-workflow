"""email table changes

Revision ID: 6d8ceb1c18cb
Revises: 25f846183f1c
Create Date: 2021-10-12 12:54:08.354995

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d8ceb1c18cb'
down_revision = '25f846183f1c'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('email', 'workflow_id')
    op.add_column('email', sa.Column('workflow_spec_id', sa.String()))


def downgrade():
    op.drop_column('email', 'workflow_spec_id')
    op.add_column('email', sa.Column('workflow_id', sa.String()))
