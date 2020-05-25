from tests.base_test import BaseTest

from crc import db
from crc.models.user import UserModel


class TestAuthentication(BaseTest):

    def test_auth_token(self):
        self.load_example_data()
        user = UserModel(uid="dhf8r")
        auth_token = user.encode_auth_token()
        self.assertTrue(isinstance(auth_token, bytes))
        self.assertEqual("dhf8r", user.decode_auth_token(auth_token).get("sub"))

    def test_backdoor_auth_creates_user(self):
        new_uid = 'lb3dp' ## Assure this user id is in the fake responses from ldap.
        self.load_example_data()
        user = db.session.query(UserModel).filter(UserModel.uid == new_uid).first()
        self.assertIsNone(user)

        user_info = {'uid': new_uid, 'first_name': 'Cordi', 'last_name': 'Nator',
                   'email_address': 'czn1z@virginia.edu'}
        redirect_url = 'http://worlds.best.website/admin'
        query_string = self.user_info_to_query_string(user_info, redirect_url)
        url = '/v1.0/sso_backdoor%s' % query_string
        rv_1 = self.app.get(url, follow_redirects=False)
        self.assertTrue(rv_1.status_code == 302)
        self.assertTrue(str.startswith(rv_1.location, redirect_url))

        user = db.session.query(UserModel).filter(UserModel.uid == new_uid).first()
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.display_name)
        self.assertIsNotNone(user.email_address)

        # Hitting the same endpoint again with the same info should not cause an error
        rv_2 = self.app.get(url, follow_redirects=False)
        self.assertTrue(rv_2.status_code == 302)
        self.assertTrue(str.startswith(rv_2.location, redirect_url))

    def test_normal_auth_creates_user(self):
        new_uid = 'lb3dp' # This user is in the test ldap system.
        self.load_example_data()
        user = db.session.query(UserModel).filter(UserModel.uid == new_uid).first()
        self.assertIsNone(user)
        redirect_url = 'http://worlds.best.website/admin'
        headers = dict(Uid=new_uid)
        rv = self.app.get('login', follow_redirects=False, headers=headers)
        self.assert_success(rv)
        user = db.session.query(UserModel).filter(UserModel.uid == new_uid).first()
        self.assertIsNotNone(user)
        self.assertEquals(new_uid, user.uid)
        self.assertEquals("Laura Barnes", user.display_name)
        self.assertEquals("lb3dp@virginia.edu", user.email_address)
        self.assertEquals("E0:Associate Professor of Systems and Information Engineering", user.title)


    def test_current_user_status(self):
        self.load_example_data()
        rv = self.app.get('/v1.0/user')
        self.assert_failure(rv, 401)

        rv = self.app.get('/v1.0/user', headers=self.logged_in_headers())
        self.assert_success(rv)

        # User must exist in the mock ldap responses.
        user = UserModel(uid="dhf8r", first_name='Dan', last_name='Funk', email_address='dhf8r@virginia.edu')
        rv = self.app.get('/v1.0/user', headers=self.logged_in_headers(user, redirect_url='http://omg.edu/lolwut'))
        self.assert_success(rv)
