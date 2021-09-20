"""empty message

Revision ID: 31b99f8f4986
Revises: 981156283cb9
Create Date: 2021-09-20 09:52:44.591606

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '31b99f8f4986'
down_revision = '981156283cb9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('file', sa.Column('sha', sa.String(), nullable=True))
    op.add_column('file_data', sa.Column('sha', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('file_data', 'sha')
    op.drop_column('file', 'sha')
    # ### end Alembic commands ###
