"""empty message

Revision ID: f28ee3722c49
Revises: cb892916166a
Create Date: 2021-03-02 08:30:22.879266

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f28ee3722c49'
down_revision = 'cb892916166a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('study', sa.Column('short_title', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('study', 'short_title')
    # ### end Alembic commands ###
