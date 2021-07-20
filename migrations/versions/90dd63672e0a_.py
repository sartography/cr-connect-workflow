"""empty message

Revision ID: 90dd63672e0a
Revises: 8856126b6658
Create Date: 2020-03-10 21:16:38.827156

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90dd63672e0a'
down_revision = '8856126b6658'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('task_event',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('study_id', sa.Integer(), nullable=False),
    sa.Column('user_uid', sa.String(), nullable=False),
    sa.Column('workflow_id', sa.Integer(), nullable=False),
    sa.Column('workflow_spec_id', sa.String(), nullable=True),
    sa.Column('spec_version', sa.String(), nullable=True),
    sa.Column('task_id', sa.String(), nullable=True),
    sa.Column('task_state', sa.String(), nullable=True),
    sa.Column('date', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['study_id'], ['study.id'], ),
    sa.ForeignKeyConstraint(['user_uid'], ['user.uid'], ),
    sa.ForeignKeyConstraint(['workflow_id'], ['workflow.id'], ),
    sa.ForeignKeyConstraint(['workflow_spec_id'], ['workflow_spec.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('workflow_stats',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('study_id', sa.Integer(), nullable=False),
    sa.Column('workflow_id', sa.Integer(), nullable=False),
    sa.Column('workflow_spec_id', sa.String(), nullable=True),
    sa.Column('spec_version', sa.String(), nullable=True),
    sa.Column('num_tasks_total', sa.Integer(), nullable=True),
    sa.Column('num_tasks_complete', sa.Integer(), nullable=True),
    sa.Column('num_tasks_incomplete', sa.Integer(), nullable=True),
    sa.Column('last_updated', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['study_id'], ['study.id'], ),
    sa.ForeignKeyConstraint(['workflow_id'], ['workflow.id'], ),
    sa.ForeignKeyConstraint(['workflow_spec_id'], ['workflow_spec.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('workflow_stats')
    op.drop_table('task_event')
    # ### end Alembic commands ###
