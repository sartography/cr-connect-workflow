import json

from tests.base_test import BaseTest


class TestLdapApi(BaseTest):

    def test_get_ldap(self):
        """
        Test to make sure that LDAP api point returns a 200 code
        """
        self.load_example_data()
        rv = self.app.get('/v1.0/ldap?query=dhf',
                          follow_redirects=True,
                          content_type="application/json", headers=self.logged_in_headers())
        self.assertTrue(rv.status_code == 200)
        user_uid = "dhf8r"
        data = json.loads(rv.data)
        self.assertEqual(data[0]['uid'], user_uid)
        self.assertEqual(data[0]['display_name'], 'Dan Funk')
        self.assertEqual(data[0]['given_name'], 'Dan')
        self.assertEqual(data[0]['affiliation'], 'faculty')



