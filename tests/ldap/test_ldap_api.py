import json

from tests.base_test import BaseTest


class TestLdapApi(BaseTest):

    def test_get_ldap(self):
        """
        Test to make sure that LDAP api returns a real user
        """
        rv = self.app.get('/v1.0/ldap?query=dhf8r',
                          follow_redirects=True,
                          content_type="application/json", headers=self.logged_in_headers())
        self.assertTrue(rv.status_code == 200)
        user_uid = "dhf8r"
        data = json.loads(rv.data)
        self.assertEqual(data[0]['uid'], user_uid)
        self.assertEqual(data[0]['display_name'], 'Dan Funk')
        self.assertEqual(data[0]['given_name'], 'Dan')
        self.assertEqual(data[0]['affiliation'], 'faculty')

    def test_not_in_ldap(self):
        """
        Test to make sure the LDAP api doesn't return a nonexistent user
        """
        rv = self.app.get('/v1.0/ldap?query=atp',
                          follow_redirects=True,
                          content_type="application/json", headers=self.logged_in_headers())
        # Should still successfully perform lookup
        self.assertTrue(rv.status_code == 200)
        data = json.loads(rv.data)
        # Should not return any users
        self.assertEqual(len(data), 0)


