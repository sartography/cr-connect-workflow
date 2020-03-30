"""empty message

Revision ID: 7c0de7621a1f
Revises: 87af86338630
Create Date: 2020-03-30 08:42:21.483856

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7c0de7621a1f'
down_revision = '87af86338630'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("COMMIT")
    op.execute("ALTER TYPE WorkflowStatus ADD VALUE 'not_started'")


def downgrade():
    pass