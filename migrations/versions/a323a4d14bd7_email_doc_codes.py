"""Store attachment doc codes for emails

Revision ID: a323a4d14bd7
Revises: 546575fa21a8
Create Date: 2022-06-15 12:24:39.298593

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a323a4d14bd7'
down_revision = '546575fa21a8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'email_doc_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email_id', sa.Integer(), nullable=False),
        sa.Column('doc_codes', sa.String()),
        sa.ForeignKeyConstraint(['email_id'], ['email.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_foreign_key('email_id_key', 'email_doc_codes', 'email', ['email_id'], ['id'])


def downgrade():
    op.drop_constraint('email_id_key', 'email_doc_codes', type_='foreignkey')
    op.drop_table('email_doc_codes')
