"""empty message

Revision ID: cb645597b71b
Revises: 53596ce86e7e
Create Date: 2019-12-27 13:50:31.336513

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cb645597b71b'
down_revision = '53596ce86e7e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('file',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('version', sa.Integer(), nullable=True),
    sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True),
    sa.Column('type', sa.Enum('bpmn', 'svg', 'dmn', name='filetype'), nullable=True),
    sa.Column('primary', sa.Boolean(), nullable=True),
    sa.Column('content_type', sa.String(), nullable=True),
    sa.Column('workflow_spec_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['workflow_spec_id'], ['workflow_spec.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('file_data',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=True),
    sa.ForeignKeyConstraint(['id'], ['file.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('file_data')
    op.drop_table('file')
    # ### end Alembic commands ###
