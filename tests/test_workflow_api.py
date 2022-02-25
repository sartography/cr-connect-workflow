from tests.base_test import BaseTest

from crc import session
from crc.models.task_event import TaskEventModel
from crc.models.user import UserModel
from crc.services.workflow_service import WorkflowService
from crc.services.workflow_spec_service import WorkflowSpecService

import json


class TestWorkflowApi(BaseTest):

    def test_get_task_events(self):

        self.add_users()
        spec = self.load_test_spec('hello_world')
        user = session.query(UserModel).first()
        self.assertIsNotNone(user)
        WorkflowService.get_workflow_from_spec(spec.id, user)

        rv = self.app.get(f'/v1.0/task_events',
                          follow_redirects=True,
                          content_type="application/json",
                          headers=self.logged_in_headers())
        self.assert_success(rv)

    def test_get_task_events_bad_spec(self):
        self.add_studies()
        workflow = self.create_workflow('hello_world')

        # add a task_event
        task_event = TaskEventModel(
            study_id=workflow.study_id,
            user_uid='dhf8r',
            workflow_id=workflow.id,
            workflow_spec_id=workflow.workflow_spec_id,
            spec_version='',
            action='',
            task_id='',
            task_name='my task name',
            task_title='my task title',
            task_state='',
            task_lane='',
            form_data='',
            mi_type='',
            mi_count=None,
            mi_index=None,
            process_name='',
            date=None
        )
        session.add(task_event)
        session.commit()

        # make sure we have a task_event
        tasks = session.query(TaskEventModel).filter(TaskEventModel.user_uid=='dhf8r').all()
        self.assertEqual(1, len(tasks))

        rv = self.app.get(f'/v1.0/task_events',
                          follow_redirects=True,
                          content_type="application/json",
                          headers=self.logged_in_headers())
        self.assert_success(rv)
        data = json.loads(rv.get_data(as_text=True))
        # make sure we get the task_event
        self.assertEqual('my task title', data[0]['task_title'])

        # delete the workflow spec
        WorkflowSpecService().delete_spec('hello_world')

        # try to get the task_event again
        rv = self.app.get(f'/v1.0/task_events',
                          follow_redirects=True,
                          content_type="application/json",
                          headers=self.logged_in_headers())
        # make sure we don't get an error, even though the spec no longer exists
        self.assert_success(rv)

        # make sure we don't get any events back.
        self.assertEqual([], rv.json)

    def test_library_code(self):

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
        self.assertEqual(len(returned['libraries']), 1)
        self.assertEqual(returned['libraries'][0], 'hello_world_lib')
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
        self.add_users()
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
        spec1 = self.workflow_spec_service.get_spec('hello_world')
        self.assertIn('hello_world_lib', spec1.libraries)

        rv = self.app.delete(f'/v1.0/workflow-specification/%s'%(spec2.id),follow_redirects=True,
                          content_type="application/json",
                          headers=self.logged_in_headers())
        spec1 = self.workflow_spec_service.get_spec('hello_world')
        self.assertNotIn('hello_world_lib', spec1.libraries)


