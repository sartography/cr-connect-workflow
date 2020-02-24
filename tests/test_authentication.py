import urllib.parse

from crc import db
from crc.models.user import UserModel
from tests.base_test import BaseTest


class TestAuthentication(BaseTest):
    test_uid = "dhf8r"

    def logged_in_headers(self, user=None, redirect_url='http://some/frontend/url'):
        if user is None:
            uid = self.test_uid
            user_info = {'uid': self.test_uid, 'first_name': 'Daniel', 'last_name': 'Funk',
                       'email_address': 'dhf8r@virginia.edu'}
        else:
            uid = user.uid
            user_info = {'uid': user.uid, 'first_name': user.first_name, 'last_name': user.last_name,
                       'email_address': user.email_address}

        query_string = self.user_info_to_query_string(user_info, redirect_url)
        rv = self.app.get("/v1.0/sso_backdoor%s" % query_string, follow_redirects=False)
        self.assertTrue(rv.status_code == 302)
        self.assertTrue(str.startswith(rv.location, redirect_url))

        user_model = UserModel.query.filter_by(uid=uid).first()
        self.assertIsNotNone(user_model.display_name)
        return dict(Authorization='Bearer ' + user_model.encode_auth_token().decode())

    def test_auth_token(self):
        self.load_example_data()
        user = UserModel(uid="dhf8r")
        auth_token = user.encode_auth_token()
        self.assertTrue(isinstance(auth_token, bytes))
        self.assertEqual("dhf8r", user.decode_auth_token(auth_token))

    def test_auth_creates_user(self):
        self.load_example_data()
        user = db.session.query(UserModel).filter(UserModel.uid == self.test_uid).first()
        self.assertIsNone(user)

        user_info = {'uid': self.test_uid, 'first_name': 'Daniel', 'last_name': 'Funk',
                   'email_address': 'dhf8r@virginia.edu'}
        redirect_url = 'http://worlds.best.website/admin'
        query_string = self.user_info_to_query_string(user_info, redirect_url)
        url = '/v1.0/sso_backdoor%s' % query_string
        rv_1 = self.app.get(url, follow_redirects=False)
        self.assertTrue(rv_1.status_code == 302)
        self.assertTrue(str.startswith(rv_1.location, redirect_url))

        user = db.session.query(UserModel).filter(UserModel.uid == self.test_uid).first()
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.display_name)
        self.assertIsNotNone(user.email_address)

        # Hitting the same endpoint again with the same info should not cause an error
        rv_2 = self.app.get(url, follow_redirects=False)
        self.assertTrue(rv_2.status_code == 302)
        self.assertTrue(str.startswith(rv_2.location, redirect_url))

    def test_current_user_status(self):
        self.load_example_data()
        rv = self.app.get('/v1.0/user')
        self.assert_failure(rv, 401)

        rv = self.app.get('/v1.0/user', headers=self.logged_in_headers())
        self.assert_success(rv)

        user = UserModel(uid="ajl2j", first_name='Aaron', last_name='Louie', email_address='ajl2j@virginia.edu')
        rv = self.app.get('/v1.0/user', headers=self.logged_in_headers(user, redirect_url='http://omg.edu/lolwut'))
        self.assert_success(rv)

    def user_info_to_query_string(self, user_info, redirect_url):
        query_string_list = []
        items = user_info.items()
        for key, value in items:
            query_string_list.append('%s=%s' % (key, urllib.parse.quote(value)))

        query_string_list.append('redirect_url=%s' % redirect_url)

        return '?%s' % '&'.join(query_string_list)


