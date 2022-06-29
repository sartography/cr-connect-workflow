"""file refactor cleanup

Revision ID: 546575fa21a8
Revises: ea1cd0f3d603
Create Date: 2022-05-20 08:11:10.540804

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '546575fa21a8'
down_revision = 'ea1cd0f3d603'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE data_store DROP CONSTRAINT IF EXISTS document_id_key")
    op.execute("DROP TABLE IF EXISTS document")
    op.execute("DROP TABLE IF EXISTS file_data")
    op.execute("DROP TABLE IF EXISTS old_file")


def downgrade():
    # This is cleanup from file refactor. There is no downgrade.
    pass
