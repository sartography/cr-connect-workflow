from tests.base_test import BaseTest

from crc import app

import io
from lxml import etree
import os


class TestDMNFromSS(BaseTest):

    def test_dmn_from_ss(self):

        filepath = os.path.join(app.root_path, '..', 'tests', 'data',
                                'dmn_from_spreadsheet', 'large_test_spreadsheet.xlsx')
        f_handle = open(filepath, 'br')
        ss_data = f_handle.read()

        data = {'file': (io.BytesIO(ss_data), 'test.xlsx')}
        rv = self.app.post('/v1.0/dmn_from_ss', data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())

        dmn_xml = rv.stream.response.data
        root = etree.fromstring(dmn_xml)
        children = root.getchildren()
        self.assertEqual('{https://www.omg.org/spec/DMN/20191111/MODEL/}decision', children[0].tag)
        self.assertEqual('{https://www.omg.org/spec/DMN/20191111/DMNDI/}DMNDI', children[1].tag)
