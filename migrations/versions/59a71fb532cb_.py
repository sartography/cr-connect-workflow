"""empty message

Revision ID: 59a71fb532cb
Revises: 1c3f88dbccc3
Create Date: 2020-08-05 19:45:53.039959

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '59a71fb532cb'
down_revision = '1c3f88dbccc3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('study_event',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('study_id', sa.Integer(), nullable=False),
    sa.Column('create_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.Enum('in_progress', 'hold', 'open_for_enrollment', 'abandoned', name='studyeventstatus'), nullable=True),
    sa.Column('comment', sa.String(), nullable=True),
    sa.Column('event_type', sa.Enum('user', 'automatic', name='studyeventtype'), nullable=True),
    sa.ForeignKeyConstraint(['study_id'], ['study.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('study_event')
    # ### end Alembic commands ###
