"""empty message

Revision ID: 4363c8bb8f1b
Revises: 
Create Date: 2019-12-16 11:25:16.540952

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4363c8bb8f1b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('requirement',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('study',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(), nullable=True),
    sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True),
    sa.Column('protocol_builder_status', sa.String(), nullable=True),
    sa.Column('primary_investigator_id', sa.String(), nullable=True),
    sa.Column('sponsor', sa.String(), nullable=True),
    sa.Column('ind_number', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user',
    sa.Column('id', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('workflow',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('requirement', sa.String(), nullable=True),
    sa.Column('bpmn_workflow_json', sa.TEXT(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('workflow')
    op.drop_table('user')
    op.drop_table('study')
    op.drop_table('requirement')
    # ### end Alembic commands ###
