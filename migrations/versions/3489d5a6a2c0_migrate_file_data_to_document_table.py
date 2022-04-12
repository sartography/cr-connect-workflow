"""migrate file data to document table

Revision ID: 3489d5a6a2c0
Revises: 92d554ab6e32
Create Date: 2022-04-11 11:34:27.392601

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError

from crc.models.file import FileModel, FileDataModel, DocumentModel
from crc import app



# revision identifiers, used by Alembic.
revision = '3489d5a6a2c0'
down_revision = '92d554ab6e32'
branch_labels = None
depends_on = None


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
                    # size = db.Column(db.Integer, default=0)  # Do we need this?
                    date_modified=file_data_model.date_created,
                    date_created=file_data_model.date_created,
                    user_uid=file_data_model.user_uid,
                    archived=archived
                )
                session.add(document_model)
                count += 1
        try:
            session.commit()
        except IntegrityError as ie:
            app.logger.info(
                f'Error migrating file data. File ID: {file_model.id}, File Data ID: {file_data_model.id}, Original error: {ie}')
            session.rollback()
        except Exception as e:
            app.logger.info(
                f'Error migrating file data. File ID: {file_model.id}, File Data ID: {file_data_model.id}, Original error: {e}')


def downgrade():
    pass
