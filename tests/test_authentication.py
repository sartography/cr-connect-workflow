from crc import db
from crc.models.user import UserModel
from tests.base_test import BaseTest


class TestAuthentication(BaseTest):

    test_uid = "dhf8r"

    def logged_in_headers(self, user=None):
        if user is None:
            uid = self.test_uid
            headers = {'uid': self.test_uid, 'first_name': 'Daniel', 'last_name': 'Funk', 'email_address': 'dhf8r@virginia.edu'}
        else:
            uid = user.uid
            headers = {'uid': user.uid, 'first_name': user.first_name, 'last_name': user.last_name, 'email_address': user.email_address}

        rv = self.app.get("/v1.0/sso_backdoor", headers=headers, follow_redirects=True,
                          content_type="application/json")
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

        headers = {'uid': self.test_uid, 'first_name': 'Daniel', 'email_address': 'dhf8r@virginia.edu'}
        rv_1 = self.app.get("/v1.0/sso_backdoor", headers=headers, follow_redirects=False)
        self.assertTrue(rv_1.status_code == 302)


        user = db.session.query(UserModel).filter(UserModel.uid == self.test_uid).first()
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.display_name)
        self.assertIsNotNone(user.email_address)

        # Hitting the same endpoint again with the same info should not cause an error
        rv_2 = self.app.get("/v1.0/sso_backdoor", headers=headers, follow_redirects=False)
        self.assertTrue(rv_1.status_code == 302)

    def test_current_user_status(self):
        self.load_example_data()
        rv = self.app.get('/v1.0/user')
        self.assert_failure(rv, 401)

        rv = self.app.get('/v1.0/user', headers=self.logged_in_headers())
        self.assert_success(rv)

        user = UserModel(uid="ajl2j", first_name='Aaron', last_name='Louie', email_address='ajl2j@virginia.edu')
        rv = self.app.get('/v1.0/user', headers=self.logged_in_headers(user))
        self.assert_success(rv)
