"""empty message

Revision ID: 0ae9742a2b14
Revises: cb3a03c10a0e
Create Date: 2020-03-04 13:18:29.509562

"""
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0ae9742a2b14'
down_revision = 'cb3a03c10a0e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('file', sa.Column('latest_version', sa.Integer(), nullable=True))
    op.drop_column('file', 'version')
    op.drop_column('file', 'last_updated')
    op.add_column('file_data', sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True))
    op.add_column('file_data', sa.Column('md5_hash', postgresql.UUID(as_uuid=True), nullable=False, server_default=str(uuid.uuid4())))
    op.alter_column('file_data', 'md5_hash', server_default=None)

    op.add_column('file_data', sa.Column('version', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('file_data', 'version')
    op.drop_column('file_data', 'md5_hash')
    op.drop_column('file_data', 'last_updated')
    op.add_column('file', sa.Column('last_updated', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.add_column('file', sa.Column('version', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_column('file', 'latest_version')
    # ### end Alembic commands ###
