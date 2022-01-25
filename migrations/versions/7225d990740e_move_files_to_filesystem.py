"""Move files to filesystem

Revision ID: 7225d990740e
Revises: 44dd9397c555
Create Date: 2021-12-14 10:52:50.785342

"""

from alembic import op
import sqlalchemy as sa

# import crc
from crc import app
from crc.models.file import FileModel, FileDataModel, LookupFileModel
from crc.services.file_service import FileService
from crc.services.spec_file_service import SpecFileService
from crc.services.reference_file_service import ReferenceFileService
from crc.services.temp_migration_service import FromFilesystemService, ToFilesystemService

from shutil import rmtree
import os

# revision identifiers, used by Alembic.
revision = '7225d990740e'
down_revision = '65b5ed6ae05b'
branch_labels = None
depends_on = None

# SYNC_FILE_ROOT = app.config['SYNC_FILE_ROOT']


def upgrade():

    """"""
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)

    op.drop_table('workflow_spec_dependency_file')
    op.add_column('lookup_file', sa.Column('file_model_id', sa.Integer(), nullable=True))
    op.add_column('lookup_file', sa.Column('last_updated', sa.DateTime(), nullable=True))
    op.create_foreign_key(None, 'lookup_file', 'file', ['file_model_id'], ['id'])

    processed_files = []
    location = SpecFileService.get_sync_file_root()
    if os.path.exists(location):
        rmtree(location)
    # Process workflow spec files
    files = session.query(FileModel).filter(FileModel.workflow_spec_id is not None).all()
    for file in files:
        if file.archived is not True:
            ToFilesystemService().write_file_to_system(session, file, location)
            processed_files.append(file.id)

    # Process reference files
    # get_reference_files only returns files where archived is False
    reference_files = ReferenceFileService.get_reference_files()
    for reference_file in reference_files:
        ToFilesystemService().write_file_to_system(session, reference_file, location)
        processed_files.append(reference_file.id)

    session.flush()
    lookups = session.query(LookupFileModel).all()
    for lookup in lookups:
        session.delete(lookup)
    session.commit()
    for file_id in processed_files:
        processed_data_models = session.query(FileDataModel).filter(FileDataModel.file_model_id==file_id).all()
        for processed_data_model in processed_data_models:
            session.delete(processed_data_model)
            session.commit()
        print(f'upgrade: in processed files: file_id: {file_id}')
    print('upgrade: done: ')


def downgrade():

    # TODO: This is a work in progress, and depends on what we do in upgrade()
    op.add_column('lookup_file', sa.Column('file_data_model_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'lookup_file', 'file', ['file_data_model_id'], ['id'])
    op.drop_constraint('lookup_file_file_model_id_key', 'lookup_file', type_='foreignkey')
    op.drop_column('lookup_file', 'file_model_id')

    op.create_table('workflow_spec_dependency_file',
        sa.Column('file_data_id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['file_data_id'], ['file_data.id'], ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflow.id'], ),
        sa.PrimaryKeyConstraint('file_data_id', 'workflow_id')
    )

    location = SpecFileService.get_sync_file_root()
    FromFilesystemService().update_file_metadata_from_filesystem(location)

    print('downgrade: ')
