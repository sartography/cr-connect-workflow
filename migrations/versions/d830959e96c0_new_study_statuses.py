"""new study statuses

Revision ID: d830959e96c0
Revises: a4f87f90cc64
Create Date: 2021-12-09 11:55:28.890437

"""
from alembic import op
import sqlalchemy as sa
from crc.models.study import StudyStatus


# revision identifiers, used by Alembic.
revision = 'd830959e96c0'
down_revision = 'a4f87f90cc64'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE StudyStatus ADD VALUE 'submitted_for_pre_review'")
    op.execute("ALTER TYPE StudyStatus ADD VALUE 'in_pre_review'")
    op.execute("ALTER TYPE StudyStatus ADD VALUE 'returned_from_pre_review'")
    op.execute("ALTER TYPE StudyStatus ADD VALUE 'pre_review_complete'")
    op.execute("ALTER TYPE StudyStatus ADD VALUE 'agenda_date_set'")
    op.execute("ALTER TYPE StudyStatus ADD VALUE 'approved'")
    op.execute("ALTER TYPE StudyStatus ADD VALUE 'approved_with_conditions'")
    op.execute("ALTER TYPE StudyStatus ADD VALUE 'deferred'")
    op.execute("ALTER TYPE StudyStatus ADD VALUE 'disapproved'")


def downgrade():
    op.execute("UPDATE study set status=null WHERE status in ("
               "'submitted_for_pre_review', 'in_pre_review', 'returned_from_pre_review', "
               "'pre_review_complete', 'agenda_date_set', 'approved', 'approved_with_conditions', "
               "'deferred', 'disapproved')")
    op.execute('ALTER TYPE StudyStatus RENAME TO ss_old;')
    op.execute("CREATE TYPE StudyStatus AS ENUM('in_progress', 'hold', 'open_for_enrollment', 'abandoned')")
    op.execute("ALTER TABLE study ALTER COLUMN status TYPE studystatus USING status::text::studystatus;")
    op.execute("update study set status = 'in_progress' where status is null")
    op.execute('DROP TYPE ss_old;')
