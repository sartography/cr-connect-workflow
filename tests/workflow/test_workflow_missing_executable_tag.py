from tests.base_test import BaseTest

from flask_bpmn.api.common import ApiError


class TestMissingExecutable(BaseTest):

    def test_missing_executable(self):
        with self.assertRaises(ApiError) as ae:
            self.create_workflow('missing_executable_tag')
        self.assertEqual('No executable process tag found. Please make sure the Executable option is set in the workflow.',
                         ae.exception.message)
