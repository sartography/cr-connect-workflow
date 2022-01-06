"""Move files to filesystem

Revision ID: 7225d990740e
Revises: 44dd9397c555
Create Date: 2021-12-14 10:52:50.785342

"""

from alembic import op
import sqlalchemy as sa

import crc
from crc import app, session
from crc.models.file import FileModel, FileDataModel, LookupFileModel
from crc.models.workflow import WorkflowSpecDependencyFile
from crc.services.file_service import FileService
from crc.services.temp_migration_service import FromFilesystemService, ToFilesystemService

import os

# revision identifiers, used by Alembic.
revision = '7225d990740e'
down_revision = '65b5ed6ae05b'
branch_labels = None
depends_on = None

SYNC_FILE_ROOT = app.config['SYNC_FILE_ROOT']


def upgrade():

    """Starting this cautiously
    Don't want to hork my dev system
    Not deleting records yet

    Originally, was only going to delete data in file_data.data
    Now, thinking about deleting the record.
    """

    processed_files = []
    # Process workflow spec files
    files = session.query(FileModel).filter(FileModel.workflow_spec_id is not None).all()
    for file in files:
        if file.archived is not True:
            ToFilesystemService().write_file_to_system(file)
            processed_files.append(file.id)

    # TODO:
    #  delete processed files from file_data table
    #  delete workflow_spec_dependency_file table
    #  delete file_data_model_id from lookup_file table
    for file_id in processed_files:
        processed_models = session.query(FileDataModel).filter(FileDataModel.file_model_id==file_id).all()
        for processed_model in processed_models:
            dependency = session.query(WorkflowSpecDependencyFile).filter(WorkflowSpecDependencyFile.file_data_id==processed_model.id).first()
            if dependency is not None:
                session.delete(dependency)
            lookups = session.query(LookupFileModel).filter(LookupFileModel.file_data_model_id==processed_model.id).all()
            for lookup in lookups:
                lookup.file_data_model_id = None
            session.delete(processed_model)
        print(f'upgrade: in processed files: file_id: {file_id}')

        session.commit()

    op.drop_table('workflow_spec_dependency_file')
    print('upgrade: done: ')


def downgrade():

    # TODO: This is a work in progress, and depends on what we do in upgrade()
    op.create_table('workflow_spec_dependency_file',
    sa.Column('file_data_id', sa.Integer(), nullable=False),
    sa.Column('workflow_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['file_data_id'], ['file_data.id'], ),
    sa.ForeignKeyConstraint(['workflow_id'], ['workflow.id'], ),
    sa.PrimaryKeyConstraint('file_data_id', 'workflow_id')
    )

    FromFilesystemService().update_file_metadata_from_filesystem(SYNC_FILE_ROOT)

    print('downgrade: ')
