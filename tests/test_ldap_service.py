from tests.base_test import BaseTest

from crc.api.common import ApiError
from crc.services.ldap_service import LdapService


class TestLdapService(BaseTest):

    def setUp(self):
        self.ldap_service = LdapService()

    def tearDown(self):
        pass

    def test_get_single_user(self):
        user_info = self.ldap_service.user_info("lb3dp")
        self.assertIsNotNone(user_info)
        self.assertEqual("lb3dp", user_info.uid)
        self.assertEqual("Laura Barnes", user_info.display_name)
        self.assertEqual("Laura", user_info.given_name)
        self.assertEqual("lb3dp@virginia.edu", user_info.email_address)
        self.assertEqual("+1 (434) 924-1723", user_info.telephone_number)
        self.assertEqual("E0:Associate Professor of Systems and Information Engineering", user_info.title)
        self.assertEqual("E0:EN-Eng Sys and Environment", user_info.department)
        self.assertEqual("faculty", user_info.affiliation)
        self.assertEqual("Staff", user_info.sponsor_type)

    def test_find_missing_user(self):
        try:
            user_info = self.ldap_service.user_info("nosuch")
            self.assertFalse(True, "An API error should be raised.")
        except ApiError as ae:
            self.assertEqual("missing_ldap_record", ae.code)