from tests.base_test import BaseTest


class TestLdapApi(BaseTest):

    def test_get_ldap(self):
        """
        Test to make sure that LDAP api point returns a 200 code
        """
        self.load_example_data()
        rv = self.app.get('/v1.0/ldap?query=atp',
                          follow_redirects=True,
                          content_type="application/json", headers=self.logged_in_headers())
        self.assertTrue(rv.status_code == 200)

