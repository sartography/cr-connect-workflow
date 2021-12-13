"""new study progress statuses

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
    op.execute("CREATE TYPE progressstatus AS ENUM('in_progress', 'submitted_for_pre_review', 'in_pre_review', 'returned_from_pre_review', 'pre_review_complete', 'agenda_date_set', 'approved', 'approved_with_conditions', 'deferred', 'disapproved')")
    op.add_column('study', sa.Column('progress_status', sa.Enum('in_progress', 'submitted_for_pre_review', 'in_pre_review', 'returned_from_pre_review', 'pre_review_complete', 'agenda_date_set', 'approved', 'approved_with_conditions', 'deferred', 'disapproved', name='progressstatus'), nullable=True))
    op.execute("update study set progress_status = 'in_progress' where status='in_progress'")


def downgrade():
    op.drop_column('study', 'progress_status')
    op.execute('DROP TYPE progressstatus')
