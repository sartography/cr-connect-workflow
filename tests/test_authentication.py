import json
from datetime import timezone, datetime
from tests.base_test import BaseTest

from crc import db, app
from crc.models.study import StudySchema
from crc.models.user import UserModel
from crc.models.protocol_builder import ProtocolBuilderStatus


class TestAuthentication(BaseTest):

    def tearDown(self):
        # Assure we set the production flag back to false.
        app.config['PRODUCTION'] = False
        super().tearDown()

    def test_auth_token(self):
        self.load_example_data()
        user = UserModel(uid="dhf8r")
        auth_token = user.encode_auth_token()
        self.assertTrue(isinstance(auth_token, bytes))
        self.assertEqual("dhf8r", user.decode_auth_token(auth_token).get("sub"))

    def test_non_production_auth_creates_user(self):
        new_uid = 'lb3dp'  ## Assure this user id is in the fake responses from ldap.
        self.load_example_data()
        user = db.session.query(UserModel).filter(UserModel.uid == new_uid).first()
        self.assertIsNone(user)

        user_info = {'uid': new_uid, 'first_name': 'Cordi', 'last_name': 'Nator',
                     'email_address': 'czn1z@virginia.edu'}
        redirect_url = 'http://worlds.best.website/admin'
        query_string = self.user_info_to_query_string(user_info, redirect_url)
        url = '/v1.0/login%s' % query_string
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

    def test_production_auth_creates_user(self):
        # Switch production mode on
        app.config['PRODUCTION'] = True

        new_uid = 'lb3dp'  # This user is in the test ldap system.
        self.load_example_data()
        user = db.session.query(UserModel).filter(UserModel.uid == new_uid).first()
        self.assertIsNone(user)
        redirect_url = 'http://worlds.best.website/admin'
        headers = dict(Uid=new_uid)

        rv = self.app.get('v1.0/login', follow_redirects=False, headers=headers)

        self.assert_success(rv)
        user = db.session.query(UserModel).filter(UserModel.uid == new_uid).first()
        self.assertIsNotNone(user)
        self.assertEquals(new_uid, user.uid)
        self.assertEquals("Laura Barnes", user.display_name)
        self.assertEquals("lb3dp@virginia.edu", user.email_address)
        self.assertEquals("E0:Associate Professor of Systems and Information Engineering", user.title)

        # Switch production mode back off
        app.config['PRODUCTION'] = False

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

    def test_admin_only_endpoints(self):
        # Switch production mode on
        app.config['PRODUCTION'] = True

        admin_uids = app.config['ADMIN_UIDS']
        self.assertGreater(len(admin_uids), 0)

        for uid in admin_uids:
            admin_headers = dict(Uid=uid)

            rv = self.app.get(
                'v1.0/login',
                follow_redirects=False,
                headers=admin_headers
            )
            self.assert_success(rv)

            admin_user = db.session.query(UserModel).filter_by(uid=uid).first()
            self.assertIsNotNone(admin_user)

            admin_study = self._make_fake_study(uid)
            print('admin_study', admin_study)

            rv_add_study = self.app.post(
                '/v1.0/study',
                content_type="application/json",
                headers=self.logged_in_headers(user=admin_user),
                data=json.dumps(StudySchema().dump(admin_study))
            )
            self.assert_success(rv_add_study, 'Admin user should be able to add a study')

            new_study = json.loads(rv.get_data(as_text=True))

            rv_del_study = self.app.delete(
                '/v1.0/study/%i' % new_study.id,
                follow_redirects=False,
                headers=self.logged_in_headers(user=admin_user)
            )
            self.assert_success(rv_del_study, 'Admin user should be able to delete a study')


        # Non-admin user should not be able to delete a study
        non_admin_uid = 'lb3dp'
        non_admin_headers = dict(Uid=non_admin_uid)

        rv = self.app.get(
            'v1.0/login',
            follow_redirects=False,
            headers=non_admin_headers
        )
        self.assert_success(rv)

        non_admin_user = db.session.query(UserModel).filter_by(uid=non_admin_uid).first()
        self.assertIsNotNone(non_admin_user)
        non_admin_study = self._make_fake_study(non_admin_uid)

        rv_add_study = self.app.post(
            '/v1.0/study',
            content_type="application/json",
            headers=self.logged_in_headers(user=non_admin_user),
            data=json.dumps(StudySchema().dump(non_admin_study))
        )
        self.assert_success(rv_add_study, 'Non-admin user should be able to add a study')

        new_study = json.loads(rv.get_data(as_text=True))

        rv_del_study = self.app.delete(
            '/v1.0/study/%i' % new_study.id,
            follow_redirects=False,
            headers=self.logged_in_headers(user=non_admin_user)
        )
        self.assert_failure(rv_del_study, 'Non-admin user should not be able to delete a study')

        # Switch production mode back off
        app.config['PRODUCTION'] = False


    def _make_fake_study(self, uid):
        return {
            "title": "blah",
            "last_updated": datetime.now(tz=timezone.utc),
            "protocol_builder_status": ProtocolBuilderStatus.ACTIVE,
            "primary_investigator_id": uid,
            "user_uid": uid,
        }
