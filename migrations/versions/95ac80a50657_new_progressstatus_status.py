"""New ProgressStatus status

Revision ID: 95ac80a50657
Revises: cedd03c24166
Create Date: 2022-04-26 12:43:21.656859

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '95ac80a50657'
down_revision = 'cedd03c24166'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE progressstatus RENAME TO progressstatus_old")
    op.execute("CREATE TYPE progressstatus AS ENUM('in_progress', 'submitted_for_pre_review', 'in_pre_review', 'returned_from_pre_review', 'pre_review_complete', 'agenda_date_set', 'approved', 'approved_with_conditions', 'deferred', 'disapproved', 'ready_for_pre_review', 'resubmitted_for_pre_review', 'finance_in_progress')")
    op.execute("ALTER TABLE study ALTER COLUMN progress_status TYPE progressstatus USING progress_status::text::progressstatus")
    op.execute("DROP TYPE progressstatus_old")


def downgrade():
    op.execute("UPDATE study SET progress_status = 'in_progress' where progress_status = 'finance_in_progress'")

    op.execute("ALTER TYPE progressstatus RENAME TO progressstatus_old")
    op.execute("CREATE TYPE progressstatus AS ENUM('in_progress', 'submitted_for_pre_review', 'in_pre_review', 'returned_from_pre_review', 'pre_review_complete', 'agenda_date_set', 'approved', 'approved_with_conditions', 'deferred', 'disapproved', 'ready_for_pre_review', 'resubmitted_for_pre_review')")
    op.execute("ALTER TABLE study ALTER COLUMN progress_status TYPE progressstatus USING progress_status::text::progressstatus")
    op.execute("DROP TYPE progressstatus_old")
