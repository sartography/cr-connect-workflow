"""empty message

Revision ID: ddd5fc9ea75b
Revises: 65f3fce6031a
Create Date: 2020-03-20 11:19:01.825283

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ddd5fc9ea75b'
down_revision = '65f3fce6031a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('file', sa.Column('irb_doc_code', sa.String(), nullable=True))
    op.add_column('file', sa.Column('is_reference', sa.Boolean(), nullable=False, default=False))
    op.alter_column('file', 'primary',
               existing_type=sa.BOOLEAN(),
               nullable=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('file', 'primary',
               existing_type=sa.BOOLEAN(),
               nullable=True)
    op.drop_column('file', 'is_reference')
    op.drop_column('file', 'irb_doc_code')
    # ### end Alembic commands ###
