import os

from crc import app
from crc.services.ldap_service import LdapService
from tests.base_test import BaseTest
from ldap3 import Server, Connection, ALL, MOCK_SYNC


class TestLdapService(BaseTest):

    def setUp(self):
        server = Server('my_fake_server')
        self.connection = Connection(server, client_strategy=MOCK_SYNC)
        file_path = os.path.abspath(os.path.join(app.root_path, '..', 'tests', 'data', 'ldap_response.json'))
        self.connection.strategy.entries_from_json(file_path)
        self.connection.bind()
        self.ldap_service = LdapService(self.connection)

    def tearDown(self):
        self.connection.unbind()

    def test_get_single_user(self):
        user_info = self.ldap_service.user_info("lb3dp")
        self.assertIsNotNone(user_info)
        self.assertEqual("Laura Barnes", user_info.display_name)
        self.assertEqual("Laura", user_info.given_name)
        self.assertEqual("lb3dp@virginia.edu", user_info.email)
        self.assertEqual("+1 (434) 924-1723", user_info.telephone_number)
        self.assertEqual("E0:Associate Professor of Systems and Information Engineering", user_info.title)
        self.assertEqual("E0:EN-Eng Sys and Environment", user_info.department)
        self.assertEqual("faculty", user_info.affiliation)
        self.assertEqual("Staff", user_info.sponsor_type)

