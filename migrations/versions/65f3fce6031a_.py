"""empty message

Revision ID: 65f3fce6031a
Revises: 5f06108116ae
Create Date: 2020-03-15 12:40:42.314190

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '65f3fce6031a'
down_revision = '5f06108116ae'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('study', sa.Column('status_spec_id', sa.String(), nullable=True))
    op.add_column('study', sa.Column('status_spec_version', sa.String(), nullable=True))
    op.create_foreign_key(None, 'study', 'workflow_spec', ['status_spec_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'study', type_='foreignkey')
    op.drop_column('study', 'status_spec_version')
    op.drop_column('study', 'status_spec_id')
    # ### end Alembic commands ###
