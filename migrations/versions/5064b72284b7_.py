"""empty message

Revision ID: 5064b72284b7
Revises: bec71f7dc652
Create Date: 2020-05-28 23:54:45.623361

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5064b72284b7'
down_revision = 'bec71f7dc652'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('lookup_file', sa.Column('field_id', sa.String(), nullable=True))
    op.add_column('lookup_file', sa.Column('is_ldap', sa.Boolean(), nullable=True))
    op.add_column('lookup_file', sa.Column('workflow_spec_id', sa.String(), nullable=True))
    op.drop_column('lookup_file', 'value_column')
    op.drop_column('lookup_file', 'label_column')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('lookup_file', sa.Column('label_column', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('lookup_file', sa.Column('value_column', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.drop_column('lookup_file', 'workflow_spec_id')
    op.drop_column('lookup_file', 'is_ldap')
    op.drop_column('lookup_file', 'field_id')
    # ### end Alembic commands ###
