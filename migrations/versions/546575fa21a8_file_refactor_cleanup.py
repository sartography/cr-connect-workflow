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
    op.drop_constraint('document_id_key', 'data_store', type_='foreignkey')
    op.drop_table('document')
    op.drop_table('file_data')
    op.drop_table('old_file')


def downgrade():
    # This is cleanup from file refactor. There is no downgrade.
    pass
