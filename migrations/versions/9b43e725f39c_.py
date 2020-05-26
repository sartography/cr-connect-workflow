"""empty message

Revision ID: 9b43e725f39c
Revises: 55c6cd407d89
Create Date: 2020-05-25 23:09:14.761831

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b43e725f39c'
down_revision = '55c6cd407d89'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('approval_file',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('file_id', sa.Integer(), nullable=False),
    sa.Column('approval_id', sa.Integer(), nullable=False),
    sa.Column('file_version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['approval_id'], ['approval.id'], ),
    sa.ForeignKeyConstraint(['file_id'], ['file.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('approval', sa.Column('date_created', sa.DateTime(timezone=True), nullable=True))
    op.add_column('approval', sa.Column('version', sa.Integer(), nullable=True))
    op.add_column('approval', sa.Column('workflow_hash', sa.String(), nullable=True))
    op.drop_column('approval', 'workflow_version')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('approval', sa.Column('workflow_version', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('approval', 'workflow_hash')
    op.drop_column('approval', 'version')
    op.drop_column('approval', 'date_created')
    op.drop_table('approval_file')
    # ### end Alembic commands ###
