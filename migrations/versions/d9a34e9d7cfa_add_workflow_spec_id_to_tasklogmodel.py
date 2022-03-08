"""Add workflow_spec_id to TaskLogModel

Revision ID: d9a34e9d7cfa
Revises: cf57eba23a16
Create Date: 2022-03-08 13:37:24.773814

"""
from alembic import op
import sqlalchemy as sa

from crc.models.task_log import TaskLogModel
from crc.models.workflow import WorkflowModel


# revision identifiers, used by Alembic.
revision = 'd9a34e9d7cfa'
down_revision = 'cf57eba23a16'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('task_log', sa.Column('workflow_spec_id', sa.String()))
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)
    session.flush()
    task_logs = session.query(TaskLogModel).all()
    for task_log in task_logs:
        workflow = session.query(WorkflowModel).filter(WorkflowModel.id==task_log.workflow_id).first()
        if workflow and workflow.workflow_spec_id:
            task_log.workflow_spec_id = workflow.workflow_spec_id
    session.commit()


def downgrade():
    op.drop_column('task_log', 'workflow_spec_id')
