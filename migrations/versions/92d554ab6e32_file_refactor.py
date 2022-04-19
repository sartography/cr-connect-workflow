"""File refactor

Revision ID: 92d554ab6e32
Revises: a345e44ecd27
Create Date: 2022-04-08 10:46:46.422328

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '92d554ab6e32'
down_revision = 'a345e44ecd27'
branch_labels = None
depends_on = None


def upgrade():
    # TODO: Fix data_store references and include data_stores, decide whether to keep size
    # data_stores = relationship(DataStoreModel, cascade="all,delete", backref="file")
    # size = db.Column(db.Integer, default=0)  # Do we need this?
    op.create_table('document',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('type', sa.String, nullable=False),
        sa.Column('content_type', sa.String(), nullable=True),
        sa.Column('workflow_id', sa.Integer(), nullable=True),
        sa.Column('task_spec', sa.String, nullable=True),
        sa.Column('irb_doc_code', sa.String, nullable=False),
        sa.Column('md5_hash', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('data', sa.LargeBinary(), nullable=True),
        sa.Column('date_modified', sa.DateTime(timezone=True), nullable=True, onupdate=sa.func.now()),
        sa.Column('date_created', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
        sa.Column('user_uid', sa.String(), nullable=True),
        sa.Column('archived', sa.Boolean(), default=False),
        sa.Column('size', sa.Integer, default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_uid'], ['user.uid'], ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflow.id'], ),
    )
    op.add_column('data_store', sa.Column('document_id', sa.Integer(), nullable=True))
    op.create_foreign_key('document_id_key', 'data_store', 'document', ['document_id'], ['id'])


def downgrade():
    op.drop_constraint('document_id_key', 'data_store', type_='foreignkey')
    op.drop_column('data_store', 'document_id')
    op.drop_table('document')
