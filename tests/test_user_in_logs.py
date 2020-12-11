from tests.base_test import BaseTest
from crc import db
from crc.models.user import UserModel
import json


class TestUserID(BaseTest):

    def test_user_id_in_request(self):
        """This assures the uid is in response via ApiError"""

        workflow = self.create_workflow('failing_workflow')
        user_uid = workflow.study.user_uid
        user = db.session.query(UserModel).filter_by(uid=user_uid).first()
        rv = self.app.get(f'/v1.0/workflow/{workflow.id}'
                          f'?soft_reset={str(False)}'
                          f'&hard_reset={str(False)}'
                          f'&do_engine_steps={str(True)}',
                          headers=self.logged_in_headers(user),
                          content_type="application/json")
        data = json.loads(rv.data)
        self.assertEqual(data['task_user'], user_uid)

    def test_user_id_in_sentry(self):
        """This assures the uid is in Sentry.
           We use this to send errors to Slack."""
        # Currently have no clue how to do this :(
        pass
