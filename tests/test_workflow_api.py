from tests.base_test import BaseTest

from crc import session
from crc.models.user import UserModel
from crc.services.user_service import UserService
from crc.services.workflow_service import WorkflowService
from crc.models.workflow import WorkflowLibraryModel

from example_data import ExampleDataLoader

import json


class TestWorkflowApi(BaseTest):

    def test_get_task_events(self):

        self.load_example_data()
        spec = self.load_test_spec('hello_world')
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
        spec1 = self.load_test_spec('hello_world')
        spec2 = self.load_test_spec('hello_world_lib', library=True)
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

    def test_library_cleanup(self):
        self.load_example_data()
        spec1 = self.load_test_spec('hello_world')
        spec2 = self.load_test_spec('hello_world_lib', library=True)
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
        lib = session.query(WorkflowLibraryModel).filter(WorkflowLibraryModel.library_spec_id==spec2.id).first()
        self.assertIsNotNone(lib)

        rv = self.app.delete(f'/v1.0/workflow-specification/%s'%(spec1.id),follow_redirects=True,
                          content_type="application/json",
                          headers=self.logged_in_headers())

        lib = session.query(WorkflowLibraryModel).filter(WorkflowLibraryModel.library_spec_id==spec2.id).first()
        self.assertIsNone(lib)


