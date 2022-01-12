from tests.base_test import BaseTest

from crc import session
from crc.models.file import FileModel
from crc.services.temp_migration_service import ToFilesystemService


# TODO: Decide what to do with this - mac 20220112
class TestFilesToFilesystem(BaseTest):

    def test_files_to_filesystem(self):
        pass

    #     self.load_example_data()
    #
    #     files = session.query(FileModel).all()
    #     for file in files:
    #         if file.archived is not True:
    #             ToFilesystemService().write_file_to_system(file)
    #
    #     print('test_files_to_filesystem')
