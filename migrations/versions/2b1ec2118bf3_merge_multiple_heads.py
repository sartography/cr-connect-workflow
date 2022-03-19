"""merge multiple heads

Revision ID: 2b1ec2118bf3
Revises: f527568787e5, f93185c45e75
Create Date: 2022-03-18 12:28:26.855504

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b1ec2118bf3'
down_revision = ('f527568787e5', 'f93185c45e75')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
