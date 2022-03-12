"""merge conflicting heads

Revision ID: 28752ce0775c
Revises: f214ee53ca26, d9a34e9d7cfa
Create Date: 2022-03-12 16:22:17.724988

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '28752ce0775c'
down_revision = ('f214ee53ca26', 'd9a34e9d7cfa')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
