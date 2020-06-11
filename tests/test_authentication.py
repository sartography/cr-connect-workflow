import json
from calendar import timegm
from datetime import timezone, datetime, timedelta
from tests.base_test import BaseTest

from crc import db, app
from crc.models.study import StudySchema, StudyModel
from crc.models.user import UserModel
from crc.models.protocol_builder import ProtocolBuilderStatus


class TestAuthentication(BaseTest):

    def tearDown(self):
        # Assure we set the production flag back to false.
        app.config['PRODUCTION'] = False
        super().tearDown()

    def test_auth_token(self):
        # Save the orginal timeout setting
        orig_ttl = float(app.config['TOKEN_AUTH_TTL_HOURS'])

        self.load_example_data()

        # Set the timeout to something else
        new_ttl = 4.0
        app.config['TOKEN_AUTH_TTL_HOURS'] = new_ttl
        user = UserModel(uid="dhf8r")
        expected_exp_1 = timegm((datetime.utcnow() + timedelta(hours=new_ttl)).utctimetuple())
        auth_token_1 = user.encode_auth_token()
        self.assertTrue(isinstance(auth_token_1, bytes))
        self.assertEqual("dhf8r", user.decode_auth_token(auth_token_1).get("sub"))
        actual_exp_1 = user.decode_auth_token(auth_token_1).get("exp")
        self.assertTrue(expected_exp_1 - 1000 <= actual_exp_1 <= expected_exp_1 + 1000)

        # Set the timeout back to where it was
        app.config['TOKEN_AUTH_TTL_HOURS'] = orig_ttl
        expected_exp_2 = timegm((datetime.utcnow() + timedelta(hours=new_ttl)).utctimetuple())
        auth_token_2 = user.encode_auth_token()
        self.assertTrue(isinstance(auth_token_2, bytes))
        actual_exp_2 = user.decode_auth_token(auth_token_1).get("exp")
        self.assertTrue(expected_exp_2 - 1000 <= actual_exp_2 <= expected_exp_2 + 1000)

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

        self.load_example_data()

        new_uid = 'lb3dp'  # This user is in the test ldap system.
        user = db.session.query(UserModel).filter_by(uid=new_uid).first()
        self.assertIsNone(user)
        redirect_url = 'http://worlds.best.website/admin'
        headers = dict(Uid=new_uid)

        rv = self.app.get('v1.0/login', follow_redirects=False, headers=headers)

        self.assert_success(rv)
        user = db.session.query(UserModel).filter_by(uid=new_uid).first()
        self.assertIsNotNone(user)
        self.assertEqual(new_uid, user.uid)
        self.assertEqual("Laura Barnes", user.display_name)
        self.assertEqual("lb3dp@virginia.edu", user.email_address)
        self.assertEqual("E0:Associate Professor of Systems and Information Engineering", user.title)

        # Switch production mode back off
        app.config['PRODUCTION'] = False
        db.session.flush()
        db.session.flush()
        db.session.flush()
        db.session.flush()
        db.session.flush()
        db.session.flush()
        db.session.flush()
        db.session.flush()

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

    def test_admin_can_access_admin_only_endpoints(self):

        # Switch production mode on
        app.config['PRODUCTION'] = True

        self.load_example_data()

        admin_uids = app.config['ADMIN_UIDS']
        self.assertGreater(len(admin_uids), 0)
        admin_uid = admin_uids[0]
        self.assertEqual(admin_uid, 'dhf8r')  # This user is in the test ldap system.
        admin_headers = dict(Uid=admin_uid)

        rv = self.app.get('v1.0/login', follow_redirects=False, headers=admin_headers)
        self.assert_success(rv)

        admin_user = db.session.query(UserModel).filter(UserModel.uid == admin_uid).first()
        self.assertIsNotNone(admin_user)
        self.assertEqual(admin_uid, admin_user.uid)

        admin_study = self._make_fake_study(admin_uid)

        admin_token_headers = dict(Authorization='Bearer ' + admin_user.encode_auth_token().decode())

        rv_add_study = self.app.post(
            '/v1.0/study',
            content_type="application/json",
            headers=admin_token_headers,
            data=json.dumps(StudySchema().dump(admin_study)),
            follow_redirects=False
        )
        self.assert_success(rv_add_study, 'Admin user should be able to add a study')

        new_admin_study = json.loads(rv_add_study.get_data(as_text=True))
        db_admin_study = db.session.query(StudyModel).filter_by(id=new_admin_study['id']).first()
        self.assertIsNotNone(db_admin_study)

        rv_del_study = self.app.delete(
            '/v1.0/study/%i' % db_admin_study.id,
            follow_redirects=False,
            headers=admin_token_headers
        )
        self.assert_success(rv_del_study, 'Admin user should be able to delete a study')

        # Switch production mode back off
        app.config['PRODUCTION'] = False

    def test_nonadmin_cannot_access_admin_only_endpoints(self):
        # Switch production mode on
        app.config['PRODUCTION'] = True

        self.load_example_data()

        # Non-admin user should not be able to delete a study
        non_admin_uid = 'lb3dp'
        admin_uids = app.config['ADMIN_UIDS']
        self.assertGreater(len(admin_uids), 0)
        self.assertNotIn(non_admin_uid, admin_uids)

        non_admin_headers = dict(Uid=non_admin_uid)

        rv = self.app.get(
            'v1.0/login',
            follow_redirects=False,
            headers=non_admin_headers
        )
        self.assert_success(rv)

        non_admin_user = db.session.query(UserModel).filter_by(uid=non_admin_uid).first()
        self.assertIsNotNone(non_admin_user)

        non_admin_token_headers = dict(Authorization='Bearer ' + non_admin_user.encode_auth_token().decode())

        non_admin_study = self._make_fake_study(non_admin_uid)

        rv_add_study = self.app.post(
            '/v1.0/study',
            content_type="application/json",
            headers=non_admin_token_headers,
            data=json.dumps(StudySchema().dump(non_admin_study))
        )
        self.assert_success(rv_add_study, 'Non-admin user should be able to add a study')

        new_non_admin_study = json.loads(rv_add_study.get_data(as_text=True))
        db_non_admin_study = db.session.query(StudyModel).filter_by(id=new_non_admin_study['id']).first()
        self.assertIsNotNone(db_non_admin_study)

        rv_non_admin_del_study = self.app.delete(
            '/v1.0/study/%i' % db_non_admin_study.id,
            follow_redirects=False,
            headers=non_admin_token_headers
        )
        self.assert_failure(rv_non_admin_del_study, 401)

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
