from tests.base_test import BaseTest

from crc import session
from crc.models.file import FileModel
from crc.services.temp_migration_service import ToFilesystemService


class TestFilesToFilesystem(BaseTest):

    def test_files_to_filesystem(self):
        self.load_example_data()

        files = session.query(FileModel).all()
        for file in files:
            if file.archived is not True:
                ToFilesystemService().write_file_to_system(file)

        print('test_files_to_filesystem')
