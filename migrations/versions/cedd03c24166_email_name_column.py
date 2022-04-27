"""email-name-column

Revision ID: cedd03c24166
Revises: 3489d5a6a2c0
Create Date: 2022-04-25 15:09:05.597408

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cedd03c24166'
down_revision = '3489d5a6a2c0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('email', sa.Column('name', sa.String(), nullable=True))


def downgrade():
    op.drop_column('email', 'name')
