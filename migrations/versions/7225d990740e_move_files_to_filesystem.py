"""Move files to filesystem

Revision ID: 7225d990740e
Revises: 44dd9397c555
Create Date: 2021-12-14 10:52:50.785342

"""

from alembic import op
import sqlalchemy as sa
from crc import app, session
from crc.models.file import FileModel
from crc.services.file_service import FileService
from crc.services.temp_migration_service import FromFilesystemService, ToFilesystemService

import os

# revision identifiers, used by Alembic.
revision = '7225d990740e'
down_revision = '65b5ed6ae05b'
branch_labels = None
depends_on = None


def upgrade():

    """Starting this cautiously
    Don't want to hork my dev system
    Not deleting records yet

    Originally, was only going to delete data in file_data.data
    Now, thinking about deleting the record.
    """

    processed_files = []
    files = session.query(FileModel).all()
    for file in files:
        if file.archived is not True:
            ToFilesystemService().write_file_to_system(file)
            processed_files.append(file.id)

    # TODO: delete processed files from file_data table

    print('upgrade: done: ')


def downgrade():

    # TODO: This is a work in progress, and depends on what we do in upgrade()
    SYNC_FILE_ROOT = os.path.join(app.root_path, '..', 'files')
    FromFilesystemService().update_file_metadata_from_filesystem(SYNC_FILE_ROOT)

    print('downgrade: ')
