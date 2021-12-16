from tests.base_test import BaseTest

from crc.services.temp_migration_service import FromFilesystemService, SYNC_FILE_ROOT


class TestFilesFromFilesystem(BaseTest):

    def test_files_from_filesystem(self):

        self.load_example_data()
        FromFilesystemService().update_file_metadata_from_filesystem(SYNC_FILE_ROOT)

        print(f'test_files_from_filesystem')
