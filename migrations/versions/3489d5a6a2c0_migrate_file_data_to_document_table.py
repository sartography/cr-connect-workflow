"""migrate file data to document table

Revision ID: 3489d5a6a2c0
Revises: 92d554ab6e32
Create Date: 2022-04-11 11:34:27.392601

"""
from alembic import op
import sqlalchemy as sa

from crc.models.data_store import DataStoreModel
from crc.models.file import OldFileModel, FileModel, FileDataModel



# revision identifiers, used by Alembic.
revision = '3489d5a6a2c0'
down_revision = '92d554ab6e32'
branch_labels = None
depends_on = None


# def update_data_store(old_file_id, file_id, session):
#     # update data_store with new fie_ids
#     data_stores = session.query(DataStoreModel).filter(DataStoreModel.file_id == old_file_id).all()
#     for data_store in data_stores:
#         data_store.file_id = file_id
#     session.commit()


def upgrade():
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)
    # session.flush()

    # migrate data from old file table and file data table to new file table
    old_file_models = session.query(OldFileModel).all()
    largest_file_id = 0
    for old_file_model in old_file_models:
        if old_file_model.irb_doc_code is not None:
            largest_file_id = max(largest_file_id, old_file_model.id)
            file_data_models = session.query(FileDataModel).\
                filter(FileDataModel.file_model_id == old_file_model.id).\
                order_by(sa.desc(FileDataModel.date_created)).\
                all()
            if len(file_data_models) > 0:
                file_data_model = file_data_models[0]
                file_model = FileModel(
                    id=old_file_model.id,
                    name=old_file_model.name,
                    type=old_file_model.type.value,
                    content_type=old_file_model.content_type,
                    workflow_id=old_file_model.workflow_id,
                    task_spec=old_file_model.task_spec,
                    irb_doc_code=old_file_model.irb_doc_code,
                    md5_hash=file_data_model.md5_hash,
                    data=file_data_model.data,
                    size=file_data_model.size,
                    date_modified=file_data_model.date_created,
                    date_created=file_data_model.date_created,
                    user_uid=file_data_model.user_uid,
                    archived=False
                )
                session.add(file_model)
                session.commit()
    sequence = FileModel.__tablename__ + '_id_seq1'
    new_start_id = largest_file_id + 1
    alter_sequence = f'ALTER SEQUENCE {sequence} RESTART WITH {new_start_id}'
    op.execute(alter_sequence)

    # Wait until data is migrated before adding foreign key restraint
    # Otherwise, file_ids don't exist
    op.create_foreign_key('file_id_key', 'data_store', 'file', ['file_id'], ['id'])


def downgrade():
    # Instead of deleting the new records here, we just drop the table in revision 92d554ab6e32
    op.drop_constraint('file_id_key', 'data_store', type_='foreignkey')
