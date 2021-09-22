"""new study info data points

Revision ID: 9afbd55082a0
Revises: 981156283cb9
Create Date: 2021-09-17 10:31:05.094062

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9afbd55082a0'
down_revision = '981156283cb9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('study', sa.Column('short_name', sa.String(), nullable=True))
    op.add_column('study', sa.Column('proposal_name', sa.String(), nullable=True))


def downgrade():
    op.drop_column('study', 'short_name')
    op.drop_column('study', 'proposal_name')
