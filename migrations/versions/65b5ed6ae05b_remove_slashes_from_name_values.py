"""Remove slashes from name values

Revision ID: 65b5ed6ae05b
Revises: 7225d990740e
Create Date: 2021-12-17 11:16:52.165479

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '65b5ed6ae05b'
down_revision = '44dd9397c555'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE file SET name = REPLACE(name, '/', '-')")
    op.execute("UPDATE workflow_spec SET display_name = REPLACE(display_name, '/', '-')")
    op.execute("UPDATE workflow_spec_category SET display_name = REPLACE(display_name, '/', '-')")


def downgrade():
    # There are already valid uses of '-' in these tables.
    # We probably don't want to change them to '/'
    # So, we pass here. No downgrade.
    pass
