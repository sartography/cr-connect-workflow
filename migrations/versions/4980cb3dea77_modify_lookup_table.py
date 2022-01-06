"""modify lookup table file_data_model_id -> file_id

Revision ID: 4980cb3dea77
Revises: 7225d990740e
Create Date: 2022-01-06 12:07:47.066325

"""
from alembic import op
import sqlalchemy as sa

from crc.models.file import FileDataModel, LookupFileModel


# revision identifiers, used by Alembic.
revision = '4980cb3dea77'
down_revision = '7225d990740e'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)

    op.add_column('lookup_file', sa.Column('file_model_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'lookup_file', 'file', ['file_model_id'], ['id'])

    lookup_file_records = session.query(LookupFileModel).all()
    for lookup in lookup_file_records:
        file_model_id = session.query(FileDataModel.file_model_id).filter(FileDataModel.id==lookup.file_data_model_id).scalar()
        lookup.file_model_id = file_model_id
        session.commit()

    op.drop_column('lookup_file', 'file_data_model_id')
    op.drop_constraint('lookup_file_file_data_model_id_fkey', 'lookup_file', type_='foreignkey')

    print('revision 4980cb3dea77: upgrade: done: ')


def downgrade():
    pass
