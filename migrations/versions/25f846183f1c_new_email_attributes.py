"""new-email-attributes

Revision ID: 25f846183f1c
Revises: 5c63a89ee7b7
Create Date: 2021-10-06 10:11:37.963712

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '25f846183f1c'
down_revision = 'ac1141d29d37'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('email', sa.Column('cc', sa.String(), nullable=True))
    op.add_column('email', sa.Column('bcc', sa.String(), nullable=True))
    op.add_column('email', sa.Column('timestamp', sa.DateTime()))
    op.add_column('email', sa.Column('workflow_id', sa.String(), nullable=True))


def downgrade():
    op.drop_column('email', 'cc')
    op.drop_column('email', 'bcc')
    op.drop_column('email', 'timestamp')
    op.drop_column('email', 'workflow_id')
