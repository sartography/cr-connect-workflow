import json
from calendar import timegm
from datetime import timezone, datetime, timedelta

import jwt

from tests.base_test import BaseTest
from crc import app, session
from crc.api.common import ApiError
from crc.models.protocol_builder import ProtocolBuilderStatus
from crc.models.study import StudySchema, StudyModel, StudyStatus
from crc.services.ldap_service import LdapService
from crc.models.user import UserModel

from unittest.mock import patch


class TestAuthentication(BaseTest):
    admin_uid = 'dhf8r'
    non_admin_uid = 'lb3dp'

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
        user_1 = UserModel(uid="dhf8r")
        expected_exp_1 = timegm((datetime.utcnow() + timedelta(hours=new_ttl)).utctimetuple())
        auth_token_1 = user_1.encode_auth_token()
        self.assertTrue(isinstance(auth_token_1, str))
        self.assertEqual("dhf8r", user_1.decode_auth_token(auth_token_1).get("sub"))
        #actual_exp_1 = user_1.decode_auth_token(auth_token_1).get("exp")
        #self.assertTrue(expected_exp_1 - 1000 <= actual_exp_1 <= expected_exp_1 + 1000)

        # # Set the timeout to something else
        # neg_ttl = -0.01
        # app.config['TOKEN_AUTH_TTL_HOURS'] = neg_ttl
        # user_2 = UserModel(uid="dhf8r")
        # expected_exp_2 = timegm((datetime.utcnow() + timedelta(hours=neg_ttl)).utctimetuple())
        # auth_token_2 = user_2.encode_auth_token()
        # self.assertTrue(isinstance(auth_token_2, bytes))
        # with self.assertRaises(ApiError) as api_error:
        #     with self.assertRaises(jwt.exceptions.ExpiredSignatureError):
        #         user_2.decode_auth_token(auth_token_2)
        # self.assertEqual(api_error.exception.status_code, 400, 'Should raise an API Error if token is expired')
        #
        # # Set the timeout back to where it was
        # app.config['TOKEN_AUTH_TTL_HOURS'] = orig_ttl
        # user_3 = UserModel(uid="dhf8r")
        # expected_exp_3 = timegm((datetime.utcnow() + timedelta(hours=new_ttl)).utctimetuple())
        # auth_token_3 = user_3.encode_auth_token()
        # self.assertTrue(isinstance(auth_token_3, bytes))
        # actual_exp_3 = user_3.decode_auth_token(auth_token_1).get("exp")
        # self.assertTrue(expected_exp_3 - 1000 <= actual_exp_3 <= expected_exp_3 + 1000)

    def test_non_production_auth_creates_user(self):
        new_uid = self.non_admin_uid  ## Assure this user id is in the fake responses from ldap.
#        self.load_example_data()
        user = session.query(UserModel).filter(UserModel.uid == new_uid).first()
        self.assertIsNone(user)

        user_info = {'uid': new_uid, 'first_name': 'Cordi', 'last_name': 'Nator',
                     'email_address': 'czn1z@virginia.edu'}
        redirect_url = 'http://worlds.best.website/admin'
        query_string = self.user_info_to_query_string(user_info, redirect_url)
        url = '/v1.0/login%s' % query_string
        rv_1 = self.app.get(url, follow_redirects=False)
        self.assertTrue(rv_1.status_code == 302)
        self.assertTrue(str.startswith(rv_1.location, redirect_url))

        user = session.query(UserModel).filter(UserModel.uid == new_uid).first()
        self.assertIsNotNone(user)
        self.assertIsNotNone(user.ldap_info.display_name)
        self.assertIsNotNone(user.ldap_info.email_address)

        # Hitting the same endpoint again with the same info should not cause an error
        rv_2 = self.app.get(url, follow_redirects=False)
        self.assertTrue(rv_2.status_code == 302)
        self.assertTrue(str.startswith(rv_2.location, redirect_url))

    def test_production_auth_creates_user(self):
        # Switch production mode on
        app.config['PRODUCTION'] = True

        self.load_example_data()

        # User should not be in the system yet.
        user = session.query(UserModel).filter(UserModel.uid == self.non_admin_uid).first()
        self.assertIsNone(user)

        # Log in
        non_admin_user = self._login_as_non_admin()

        # User should be in the system now.
        redirect_url = 'http://worlds.best.website/admin'
        rv_user = self.app.get('/v1.0/user', headers=self.logged_in_headers(non_admin_user, redirect_url=redirect_url))
        self.assert_success(rv_user)
        user_data = json.loads(rv_user.get_data(as_text=True))
        self.assertEqual(self.non_admin_uid, user_data['uid'])
        self.assertFalse(user_data['is_admin'])

        # Switch production mode back off
        app.config['PRODUCTION'] = False

    def test_current_user_status(self):
        self.load_example_data()
        rv = self.app.get('/v1.0/user')
        self.assert_failure(rv, 401)

        rv = self.app.get('/v1.0/user', headers=self.logged_in_headers())
        self.assert_success(rv)

        # User must exist in the mock ldap responses.
        user = UserModel(uid="dhf8r", ldap_info=LdapService.user_info("dhf8r"))
        rv = self.app.get('/v1.0/user', headers=self.logged_in_headers(user, redirect_url='http://omg.edu/lolwut'))
        self.assert_success(rv)
        user_data = json.loads(rv.get_data(as_text=True))
        self.assertTrue(user_data['is_admin'])

    def test_admin_can_access_admin_only_endpoints(self):
        # Switch production mode on
        app.config['PRODUCTION'] = True

        self.load_example_data()

        admin_user = self._login_as_admin()
        admin_study = self._make_fake_study(admin_user.uid)
        admin_token_headers = dict(Authorization='Bearer ' + admin_user.encode_auth_token())

        rv_add_study = self.app.post(
            '/v1.0/study',
            content_type="application/json",
            headers=admin_token_headers,
            data=json.dumps(StudySchema().dump(admin_study)),
            follow_redirects=False
        )
        self.assert_success(rv_add_study, 'Admin user should be able to add a study')

        new_admin_study = json.loads(rv_add_study.get_data(as_text=True))
        db_admin_study = session.query(StudyModel).filter_by(id=new_admin_study['id']).first()
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
        non_admin_user = self._login_as_non_admin()
        non_admin_token_headers = dict(Authorization='Bearer ' + non_admin_user.encode_auth_token())
        non_admin_study = self._make_fake_study(non_admin_user.uid)

        rv_add_study = self.app.post(
            '/v1.0/study',
            content_type="application/json",
            headers=non_admin_token_headers,
            data=json.dumps(StudySchema().dump(non_admin_study))
        )
        self.assert_success(rv_add_study, 'Non-admin user should be able to add a study')

        new_non_admin_study = json.loads(rv_add_study.get_data(as_text=True))
        db_non_admin_study = session.query(StudyModel).filter_by(id=new_non_admin_study['id']).first()
        self.assertIsNotNone(db_non_admin_study)

        rv_non_admin_del_study = self.app.delete(
            '/v1.0/study/%i' % db_non_admin_study.id,
            follow_redirects=False,
            headers=non_admin_token_headers
        )
        self.assert_failure(rv_non_admin_del_study, 401)

        # Switch production mode back off
        app.config['PRODUCTION'] = False

    def test_list_all_users(self):
        self.load_example_data()
        rv = self.app.get('/v1.0/user')
        self.assert_failure(rv, 401)

        rv = self.app.get('/v1.0/user', headers=self.logged_in_headers())
        self.assert_success(rv)

        all_users = session.query(UserModel).all()

        rv = self.app.get('/v1.0/list_users', headers=self.logged_in_headers())
        self.assert_success(rv)
        user_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(len(user_data), len(all_users))

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    def test_admin_can_impersonate_another_user(self, mock_details):
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)
        # Switch production mode on
        app.config['PRODUCTION'] = True

        self.load_example_data()

        admin_user = self._login_as_admin()
        admin_token_headers = dict(Authorization='Bearer ' + admin_user.encode_auth_token())

        # User should not be in the system yet.
        non_admin_user = session.query(UserModel).filter(UserModel.uid == self.non_admin_uid).first()
        self.assertIsNone(non_admin_user)

        # Admin should not be able to impersonate non-existent user
        rv_1 = self.app.get(
            '/v1.0/user?admin_impersonate_uid=' + self.non_admin_uid,
            content_type="application/json",
            headers=admin_token_headers,
            follow_redirects=False
        )
        self.assert_failure(rv_1, 400)

        # Add the non-admin user now
        self.logout()
        non_admin_user = self._login_as_non_admin()
        self.assertEqual(non_admin_user.uid, self.non_admin_uid)
        non_admin_token_headers = dict(Authorization='Bearer ' + non_admin_user.encode_auth_token())

        # Add a study for the non-admin user
        non_admin_study = self._make_fake_study(self.non_admin_uid)
        rv_add_study = self.app.post(
            '/v1.0/study',
            content_type="application/json",
            headers=non_admin_token_headers,
            data=json.dumps(StudySchema().dump(non_admin_study))
        )
        self.assert_success(rv_add_study, 'Non-admin user should be able to add a study')
        self.logout()

        # Admin should be able to impersonate user now
        admin_user = self._login_as_admin()
        rv_2 = self.app.get(
            '/v1.0/user?admin_impersonate_uid=' + self.non_admin_uid,
            content_type="application/json",
            headers=admin_token_headers,
            follow_redirects=False
        )
        self.assert_success(rv_2)
        user_data_2 = json.loads(rv_2.get_data(as_text=True))
        self.assertEqual(user_data_2['uid'], self.non_admin_uid, 'Admin user should impersonate non-admin user')

        # Study endpoint should return non-admin user's studies
        rv_study = self.app.get(
            '/v1.0/study',
            content_type="application/json",
            headers=admin_token_headers,
            follow_redirects=False
        )
        self.assert_success(rv_study, 'Admin user should be able to get impersonated user studies')
        study_data = json.loads(rv_study.get_data(as_text=True))
        self.assertGreaterEqual(len(study_data), 1)
        self.assertEqual(study_data[0]['user_uid'], self.non_admin_uid)

        # Switch production mode back off
        app.config['PRODUCTION'] = False

    def _make_fake_study(self, uid):
        return {
            "title": "blah",
            "last_updated": datetime.utcnow(),
            "status": StudyStatus.in_progress,
            "primary_investigator_id": uid,
            "user_uid": uid,
        }

    def _login_as_admin(self):
        admin_uids = app.config['ADMIN_UIDS']
        self.assertGreater(len(admin_uids), 0)
        self.assertIn(self.admin_uid, admin_uids)
        admin_headers = dict(Uid=self.admin_uid)

        rv = self.app.get('v1.0/login', follow_redirects=False, headers=admin_headers)
        self.assert_success(rv)

        admin_user = session.query(UserModel).filter(UserModel.uid == self.admin_uid).first()
        self.assertIsNotNone(admin_user)
        self.assertEqual(self.admin_uid, admin_user.uid)
        self.assertTrue(admin_user.is_admin())
        return admin_user

    def _login_as_non_admin(self):
        admin_uids = app.config['ADMIN_UIDS']
        self.assertGreater(len(admin_uids), 0)
        self.assertNotIn(self.non_admin_uid, admin_uids)

        non_admin_headers = dict(Uid=self.non_admin_uid)

        rv = self.app.get(
            'v1.0/login?uid=' + self.non_admin_uid,
            follow_redirects=False,
            headers=non_admin_headers
        )
        self.assert_success(rv)

        user = session.query(UserModel).filter(UserModel.uid == self.non_admin_uid).first()
        self.assertIsNotNone(user)
        self.assertFalse(user.is_admin())
        self.assertIsNotNone(user)
        self.assertEqual(self.non_admin_uid, user.uid)
        self.assertEqual("Laura Barnes", user.ldap_info.display_name)
        self.assertEqual("lb3dp@virginia.edu", user.ldap_info.email_address)
        self.assertEqual("E0:Associate Professor of Systems and Information Engineering", user.ldap_info.title)
        return user
