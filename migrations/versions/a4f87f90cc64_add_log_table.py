"""add log table

Revision ID: a4f87f90cc64
Revises: ba6df7e560a1
Create Date: 2021-10-27 10:54:40.233325

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4f87f90cc64'
down_revision = 'ba6df7e560a1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('task_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('level', sa.String(), nullable=True),
    sa.Column('code', sa.String(), nullable=True),
    sa.Column('message', sa.String(), nullable=True),
    sa.Column('study_id', sa.Integer(), nullable=False),
    sa.Column('workflow_id', sa.Integer(), nullable=False),
    sa.Column('task', sa.String(), nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['study_id'], ['study.id'], ),
    sa.ForeignKeyConstraint(['workflow_id'], ['workflow.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('task_log')
