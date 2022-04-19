"""migrate file data to document table

Revision ID: 3489d5a6a2c0
Revises: 92d554ab6e32
Create Date: 2022-04-11 11:34:27.392601

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from crc import app
from crc.models.data_store import DataStoreModel
from crc.models.file import FileModel, FileDataModel, DocumentModel



# revision identifiers, used by Alembic.
revision = '3489d5a6a2c0'
down_revision = '92d554ab6e32'
branch_labels = None
depends_on = None


def update_data_store(file_id, document_id, session):
    data_stores = session.query(DataStoreModel).filter(DataStoreModel.file_id == file_id).all()
    for data_store in data_stores:
        data_store.document_id = document_id
    session.commit()


def upgrade():
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)
    # session.flush()

    file_models = session.query(FileModel).all()
    for file_model in file_models:
        if file_model.irb_doc_code is not None:
            file_data_models = session.query(FileDataModel).\
                filter(FileDataModel.file_model_id == file_model.id).\
                order_by(sa.desc(FileDataModel.date_created)).\
                all()
            count = 0
            for file_data_model in file_data_models:
                archived = count > 0
                document_model = DocumentModel(
                    # id=file_model.id,
                    name=file_model.name,
                    type=file_model.type.value,
                    content_type=file_model.content_type,
                    workflow_id=file_model.workflow_id,
                    task_spec=file_model.task_spec,
                    irb_doc_code=file_model.irb_doc_code,
                    # data_stores = relationship(DataStoreModel, cascade="all,delete", backref="file")
                    md5_hash=file_data_model.md5_hash,
                    data=file_data_model.data,
                    size=file_data_model.size,
                    date_modified=file_data_model.date_created,
                    date_created=file_data_model.date_created,
                    user_uid=file_data_model.user_uid,
                    archived=archived
                )
                session.add(document_model)
                session.commit()
                count += 1
                update_data_store(file_model.id, document_model.id, session)
        # try:
        #     session.commit()
        # except IntegrityError as ie:
        #     app.logger.info(
        #         f'Error migrating file data. File ID: {file_model.id}, File Data ID: {file_data_model.id}, Original error: {ie}')
        #     session.rollback()
        # except Exception as e:
        #     app.logger.info(
        #         f'Error migrating file data. File ID: {file_model.id}, File Data ID: {file_data_model.id}, Original error: {e}')
    # op.drop_constraint('file_id_key', 'data_store', type_='foreignkey')
    # op.drop_column('data_store', 'file_id')


def downgrade():
    # op.add_column('data_store', sa.Column('file_id', sa.Integer(), nullable=True))
    # op.create_foreign_key('file_id_key', 'data_store', 'file', ['file_id'], ['id'])
    op.execute('UPDATE data_store SET document_id = null')
    op.execute('DELETE FROM document;')
