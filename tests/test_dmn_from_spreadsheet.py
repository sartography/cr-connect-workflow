from tests.base_test import BaseTest

from crc import app
from crc.api.file import dmn_from_ss
from crc.services.file_service import FileService

import io
import os


class TestDMNFromSS(BaseTest):

    def test_dmn_from_ss(self):

        filepath = os.path.join(app.root_path, '..', 'tests', 'data',
                                'dmn_from_spreadsheet', 'large_test_spreadsheet.xlsx')
        f_handle = open(filepath, 'br')
        ss_data = f_handle.read()

        result = dmn_from_ss(ss_data)

        print('test_dmn_from_ss')
