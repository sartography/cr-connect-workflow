"""merge multiple heads

Revision ID: a345e44ecd27
Revises: 2b1ec2118bf3, 8f0d445dd297
Create Date: 2022-03-18 12:40:48.019863

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a345e44ecd27'
down_revision = ('2b1ec2118bf3', '8f0d445dd297')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
