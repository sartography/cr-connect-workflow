"""new study status 'cr_connect_complete'

Revision ID: cf57eba23a16
Revises: 3c56c894ff5c
Create Date: 2022-03-03 08:04:24.292180

"""
from alembic import op
import sqlalchemy as sa

from crc.models.study import StudyModel, StudyStatus

# revision identifiers, used by Alembic.
revision = 'cf57eba23a16'
down_revision = '3c56c894ff5c'
branch_labels = None
depends_on = None


def upgrade():
    # add cr_connect_complete to studystatus
    op.execute('ALTER TYPE studystatus RENAME TO studystatus_old;')
    op.execute("CREATE TYPE studystatus AS ENUM('in_progress', 'hold', 'open_for_enrollment', 'abandoned', 'cr_connect_complete')")
    op.execute("ALTER TABLE study ALTER COLUMN status TYPE studystatus USING status::text::studystatus;")
    op.execute('DROP TYPE studystatus_old;')


def downgrade():
    # Removing cr_connect_complete, so change those to in_progress first
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)
    session.flush()
    studies = session.query(StudyModel).filter(StudyModel.status=='cr_connect_complete').all()
    for study in studies:
        study.status = StudyStatus('in_progress')
    session.commit()

    # delete cr_connect_complete from studystatus
    op.execute('ALTER TYPE studystatus RENAME TO studystatus_old;')
    op.execute("CREATE TYPE studystatus AS ENUM('in_progress', 'hold', 'open_for_enrollment', 'abandoned')")
    op.execute("ALTER TABLE study ALTER COLUMN status TYPE studystatus USING status::text::studystatus;")
    op.execute('DROP TYPE studystatus_old;')
