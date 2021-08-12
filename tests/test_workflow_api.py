from tests.base_test import BaseTest

from crc import session
from crc.models.user import UserModel
from crc.services.user_service import UserService
from crc.services.workflow_service import WorkflowService

from example_data import ExampleDataLoader

import json


class TestWorkflowApi(BaseTest):

    def test_get_task_events(self):

        self.load_example_data()
        spec = ExampleDataLoader().create_spec('hello_world', 'Hello World', category_id=0, standalone=True, from_tests=True)
        user = session.query(UserModel).first()
        self.assertIsNotNone(user)
        WorkflowService.get_workflow_from_spec(spec.id, user)

        rv = self.app.get(f'/v1.0/task_events',
                          follow_redirects=True,
                          content_type="application/json",
                          headers=self.logged_in_headers())
        self.assert_success(rv)


    def test_library_code(self):
        self.load_example_data()
        spec1 = ExampleDataLoader().create_spec('hello_world', 'Hello World', category_id=0, library=False,
                                               from_tests=True)

        spec2 = ExampleDataLoader().create_spec('hello_world_lib', 'Hello World Library', category_id=0, library=True,
                                               from_tests=True)
        user = session.query(UserModel).first()
        self.assertIsNotNone(user)

        rv = self.app.post(f'/v1.0/workflow-specification/%s/library/%s'%(spec1.id,spec2.id),
                          follow_redirects=True,
                          content_type="application/json",
                          headers=self.logged_in_headers())
        self.assert_success(rv)

        rv = self.app.get(f'/v1.0/workflow-specification/%s'%spec1.id,follow_redirects=True,
                          content_type="application/json",
                          headers=self.logged_in_headers())
        returned=rv.json
        self.assertIsNotNone(returned.get('libraries'))
        self.assertEqual(len(returned['libraries']),1)
        self.assertEqual(returned['libraries'][0].get('id'),'hello_world_lib')
        rv = self.app.delete(f'/v1.0/workflow-specification/%s/library/%s'%(spec1.id,spec2.id),follow_redirects=True,
                          content_type="application/json",
                          headers=self.logged_in_headers())
        rv = self.app.get(f'/v1.0/workflow-specification/%s'%spec1.id,follow_redirects=True,
                          content_type="application/json",
                          headers=self.logged_in_headers())
        returned=rv.json
        self.assertIsNotNone(returned.get('libraries'))
        self.assertEqual(len(returned['libraries']),0)



