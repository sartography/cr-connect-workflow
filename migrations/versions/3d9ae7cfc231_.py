"""Remove HSR Number

Revision ID: 3d9ae7cfc231
Revises: 2a6f7ea00e5f
Create Date: 2021-08-16 11:28:40.027495

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d9ae7cfc231'
down_revision = '2a6f7ea00e5f'
branch_labels = None
depends_on = None


def upgrade():
    # Remove `hsr_assigned` values from Study table
    op.execute("UPDATE study SET irb_status = 'incomplete_in_protocol_builder' where irb_status = 'hsr_assigned'")

    # Remove `hsr_assigned` from IRB Status Enum
    op.execute("ALTER TYPE irbstatus RENAME TO irbstatus_old")
    op.execute("CREATE TYPE irbstatus AS ENUM('incomplete_in_protocol_builder', 'completed_in_protocol_builder')")
    op.execute("ALTER TABLE study ALTER COLUMN irb_status TYPE irbstatus USING irb_status::text::irbstatus")
    op.execute("DROP TYPE irbstatus_old")

    # Remove hsr_number column from Study table
    op.drop_column('study', 'hsr_number')



def downgrade():
    op.execute("ALTER TYPE irbstatus RENAME TO irbstatus_old")
    op.execute("CREATE TYPE irbstatus AS ENUM('incomplete_in_protocol_builder', 'completed_in_protocol_builder', 'hsr_assigned')")
    op.execute("ALTER TABLE study ALTER COLUMN irb_status TYPE irbstatus USING irb_status::text::irbstatus")
    op.execute("DROP TYPE irbstatus_old")

    op.add_column('study', sa.Column('hsr_number', sa.String(), nullable=True))
