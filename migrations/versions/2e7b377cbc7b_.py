"""empty message

Revision ID: 2e7b377cbc7b
Revises: c4ddb69e7ef4
Create Date: 2020-07-28 17:03:23.586828

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2e7b377cbc7b'
down_revision = 'c4ddb69e7ef4'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('update study set protocol_builder_status = NULL;')
    op.execute('ALTER TYPE protocolbuilderstatus RENAME TO pbs_old;')
    op.execute("CREATE TYPE protocolbuilderstatus AS ENUM('incomplete', 'active', 'hold', 'open', 'abandoned')")
    op.execute("ALTER TABLE study ALTER COLUMN protocol_builder_status TYPE protocolbuilderstatus USING protocol_builder_status::text::protocolbuilderstatus;")
    op.execute('DROP TYPE pbs_old;')
    op.execute("update study set protocol_builder_status = 'incomplete';")

def downgrade():
    op.execute('update study set protocol_builder_status = NULL;')
    op.execute('ALTER TYPE protocolbuilderstatus RENAME TO pbs_old;')
    op.execute("CREATE TYPE protocolbuilderstatus AS ENUM('INCOMPLETE', 'ACTIVE', 'HOLD', 'OPEN', 'ABANDONED')")
    op.execute("ALTER TABLE study ALTER COLUMN protocol_builder_status TYPE protocolbuilderstatus USING protocol_builder_status::text::protocolbuilderstatus;")
    op.execute('DROP TYPE pbs_old;')
