"""empty message

Revision ID: 0718ad13e5f3
Revises: 69081f1ff387
Create Date: 2020-11-06 11:08:33.657440

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0718ad13e5f3'
down_revision = '69081f1ff387'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('data_store',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(), nullable=False),
    sa.Column('value', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('data_store')
    # ### end Alembic commands ###
