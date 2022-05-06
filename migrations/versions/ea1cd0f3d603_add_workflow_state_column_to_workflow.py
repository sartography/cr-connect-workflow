"""add-workflow-state-column-to-workflow

Revision ID: ea1cd0f3d603
Revises: 95ac80a50657
Create Date: 2022-04-29 13:58:35.304607

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ea1cd0f3d603'
down_revision = '95ac80a50657'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('workflow', sa.Column('state', sa.String(), nullable=True))


def downgrade():
    op.drop_column('workflow', 'state')
