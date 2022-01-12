from tests.base_test import BaseTest

from crc import app
from crc.services.temp_migration_service import FromFilesystemService
from crc.services.spec_file_service import SpecFileService

SYNC_FILE_ROOT = SpecFileService.get_sync_file_root()


# TODO: Decide what to do with this - mac 20220112
class TestFilesFromFilesystem(BaseTest):

    def test_files_from_filesystem(self):
        pass

    #
    #     self.load_example_data()
    #     FromFilesystemService().update_file_metadata_from_filesystem(SYNC_FILE_ROOT)
    #
    #     print(f'test_files_from_filesystem')
