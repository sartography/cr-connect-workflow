from crc.api.common import ApiError
from tests.base_test import BaseTest


class TestUserID(BaseTest):

    def test_user_id(self):
        # try:
        #     False
        # except:
        #     raise ApiError

        # ApiError()
        # self.assertEqual(True,False)

        # with self.assertRaises(ApiError) as api_error:
        #     self.assertEqual(2, 3)
        workflow = self.create_workflow('email')
        first_task = self.get_workflow_api(workflow).next_task

        raise ApiError('unknown_approval', 'Please provide a valid Approval ID.')
