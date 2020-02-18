from crc import db
from crc.models.user import UserModel
from tests.base_test import BaseTest


class TestAuthentication(BaseTest):

    test_uid = "dhf8r"

    def logged_in_headers(self, user=None):

        if user is None:
            uid = self.test_uid
            headers = {'uid': self.test_uid, 'givenName': 'Daniel', 'mail': 'dhf8r@virginia.edu'}
        else:
            uid = user.uid
            headers = {'uid': user.uid, 'givenName': user.display_name, 'email': user.email_address}

        rv = self.app.get("/v1.0/sso_backdoor/" + self.test_uid, follow_redirects=True,
                          content_type="application/json")
        user_model = UserModel.query.filter_by(uid=uid).first()
        return dict(Authorization='Bearer ' + user_model.encode_auth_token().decode())

    def test_auth_token(self):
        user = UserModel(uid="dhf8r")
        auth_token = user.encode_auth_token()
        self.assertTrue(isinstance(auth_token, bytes))
        self.assertEqual("dhf8r", user.decode_auth_token(auth_token))

    def test_auth_creates_user(self):
        user = db.session.query(UserModel).filter(UserModel.uid == self.test_uid).first()
        self.assertIsNone(user)

        headers = {'uid': self.test_uid, 'givenName': 'Daniel', 'mail': 'dhf8r@virginia.edu'}
        rv = self.app.get("/v1.0/sso_backdoor/" + self.test_uid, headers=headers, follow_redirects=True,
                          content_type="application/json")
        user = db.session.query(UserModel).filter(UserModel.uid == self.test_uid).first()
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.display_name)
        self.assertIsNotNone(user.email_address)

    def test_current_user_status(self):
        rv = self.app.get('/v1.0/user')
        self.assert_failure(rv, 401)

        rv = self.app.get('/v1.0/user', headers=self.logged_in_headers())
        self.assert_success(rv)
