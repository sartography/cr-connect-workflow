"""empty message

Revision ID: 1c3f88dbccc3
Revises: 2e7b377cbc7b
Create Date: 2020-07-30 18:51:01.816284

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1c3f88dbccc3'
down_revision = '2e7b377cbc7b'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE TYPE irbstatus AS ENUM('incomplete_in_protocol_builder', 'completed_in_protocol_builder', 'hsr_assigned')")
    op.execute("CREATE TYPE studystatus AS ENUM('in_progress', 'hold', 'open_for_enrollment', 'abandoned')")
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('study', sa.Column('irb_status', sa.Enum('incomplete_in_protocol_builder', 'completed_in_protocol_builder', 'hsr_assigned', name='irbstatus'), nullable=True))
    op.add_column('study', sa.Column('status', sa.Enum('in_progress', 'hold', 'open_for_enrollment', 'abandoned', name='studystatus'), nullable=True))
    op.drop_column('study', 'protocol_builder_status')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('study', sa.Column('protocol_builder_status', postgresql.ENUM('incomplete', 'active', 'hold', 'open', 'abandoned', name='protocolbuilderstatus'), autoincrement=False, nullable=True))
    op.drop_column('study', 'status')
    op.drop_column('study', 'irb_status')
    # ### end Alembic commands ###
    op.execute('DROP TYPE studystatus')
    op.execute('DROP TYPE irbstatus')
