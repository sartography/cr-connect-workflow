"""new workflow status

Revision ID: 44dd9397c555
Revises: d830959e96c0
Create Date: 2021-12-09 14:03:45.526308

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '44dd9397c555'
down_revision = 'd830959e96c0'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE WorkflowStatus ADD VALUE 'erroring'")


def downgrade():
    op.execute("UPDATE workflow set status='waiting' WHERE status = 'erroring'")
    op.execute('ALTER TYPE WorkflowStatus RENAME TO ws_old;')
    op.execute("CREATE TYPE WorkflowStatus AS ENUM('not_started', 'user_input_required', 'waiting', 'complete')")
    op.execute("ALTER TABLE workflow ALTER COLUMN status TYPE workflowstatus USING status::text::workflowstatus;")
    op.execute('DROP TYPE ws_old;')
