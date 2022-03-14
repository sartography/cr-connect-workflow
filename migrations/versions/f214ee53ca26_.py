"""empty message

Revision ID: f214ee53ca26
Revises: cf57eba23a16
Create Date: 2022-03-12 15:03:32.193996

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from crc.models.study import StudyModel, ProgressStatus

revision = 'f214ee53ca26'
down_revision = 'cf57eba23a16'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TYPE progressstatus RENAME TO progressstatus_old;')
    op.execute(
            "CREATE TYPE progressstatus AS ENUM('in_progress', 'submitted_for_pre_review', 'in_pre_review', "
            "'returned_from_pre_review', 'pre_review_complete', 'agenda_date_set', 'approved', "
            "'approved_with_conditions', 'deferred', 'disapproved', "
            "'ready_for_pre_review', 'resubmitted_for_pre_review')")
    op.execute("ALTER TABLE study ALTER COLUMN progress_status TYPE "
               "progressstatus USING progress_status::text::progressstatus;")
    op.execute('DROP TYPE progressstatus_old;')

def downgrade():
    # Removing ready_for_pre_review, resubmitted_for_pre_review, so change those to in_progress first
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)
    session.flush()
    studies = session.query(StudyModel).filter(
        StudyModel.progress_status == 'ready_for_pre_review' or StudyModel.progress_status == 'resubmitted_for_pre_review').all()
    for study in studies:
        study.progress_status = ProgressStatus('in_progress')
    session.commit()

    # delete those statuses from progress status
    op.execute('ALTER TYPE progressstatus RENAME TO progressstatus_old;')
    op.execute("CREATE TYPE progressstatus AS ENUM('in_progress', 'submitted_for_pre_review', "
               "'in_pre_review', 'returned_from_pre_review', 'pre_review_complete', "
               "'agenda_date_set', 'approved', 'approved_with_conditions', 'deferred', 'disapproved')")
    op.execute("ALTER TABLE study ALTER COLUMN progress_status"
               " TYPE progressstatus USING progress_status::text::progressstatus;")
    op.execute('DROP TYPE progressstatus_old;')
