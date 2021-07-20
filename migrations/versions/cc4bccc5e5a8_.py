"""empty message

Revision ID: cc4bccc5e5a8
Revises: 1685be1cc232
Create Date: 2020-05-04 11:15:46.266296

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'cc4bccc5e5a8'
down_revision = '1685be1cc232'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('workflow_stats')
    op.add_column('task_event', sa.Column('action', sa.String(), nullable=True))
    op.add_column('task_event', sa.Column('mi_count', sa.Integer(), nullable=True))
    op.add_column('task_event', sa.Column('mi_index', sa.Integer(), nullable=True))
    op.add_column('task_event', sa.Column('mi_type', sa.String(), nullable=True))
    op.add_column('task_event', sa.Column('process_name', sa.String(), nullable=True))
    op.add_column('task_event', sa.Column('task_name', sa.String(), nullable=True))
    op.add_column('task_event', sa.Column('task_title', sa.String(), nullable=True))
    op.add_column('task_event', sa.Column('task_type', sa.String(), nullable=True))
    op.add_column('workflow', sa.Column('last_updated', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('workflow', 'last_updated')
    op.drop_column('task_event', 'task_type')
    op.drop_column('task_event', 'task_title')
    op.drop_column('task_event', 'task_name')
    op.drop_column('task_event', 'process_name')
    op.drop_column('task_event', 'mi_type')
    op.drop_column('task_event', 'mi_index')
    op.drop_column('task_event', 'mi_count')
    op.drop_column('task_event', 'action')
    op.create_table('workflow_stats',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('study_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('workflow_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('workflow_spec_id', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('spec_version', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('num_tasks_total', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('num_tasks_complete', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('num_tasks_incomplete', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('last_updated', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['study_id'], ['study.id'], name='workflow_stats_study_id_fkey'),
    sa.ForeignKeyConstraint(['workflow_id'], ['workflow.id'], name='workflow_stats_workflow_id_fkey'),
    sa.ForeignKeyConstraint(['workflow_spec_id'], ['workflow_spec.id'], name='workflow_stats_workflow_spec_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='workflow_stats_pkey')
    )
    # ### end Alembic commands ###
