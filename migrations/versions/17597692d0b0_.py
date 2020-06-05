"""empty message

Revision ID: 17597692d0b0
Revises: 13424d5a6de8
Create Date: 2020-06-03 17:33:56.454339

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '17597692d0b0'
down_revision = '13424d5a6de8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('file', sa.Column('archived', sa.Boolean(), nullable=True, default=False))
    op.execute("UPDATE file SET archived = false")
    op.alter_column('file', 'archived', nullable=False)

def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('file', 'archived')
    # ### end Alembic commands ###
