"""remove name from spec and category

Revision ID: 8580676e5302
Revises: 5c63a89ee7b7
Create Date: 2021-10-04 11:58:41.290139

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8580676e5302'
down_revision = '5c63a89ee7b7'
branch_labels = None
depends_on = None


def upgrade():

    op.drop_column('workflow_spec_category', 'name')
    op.drop_column('workflow_spec', 'name')


def downgrade():
    op.add_column('workflow_spec_category', sa.Column('name', sa.String()))
    op.add_column('workflow_spec', sa.Column('name', sa.String()))
