from tests.base_test import BaseTest

from crc.services.user_service import UserService


class TestLanePermissions(BaseTest):
    """Can users access tasks appropriately in lanes."""

    def test_can_has_permissions(self):
        """The workflow has a lane named `Reviewer`
           lb3dp is assigned to the Reviewer lane
           dhf8r is an admin account
           start the workflow with lje5u"""

        self.add_users()  # This adds dhf8r and lb3dp
        # We need a third user
        self.create_user(uid="lje5u", email="test_user@example.com", display_name="Test User")

        # Start the workflow as user lje5u
        workflow = self.create_workflow('lane_permissions', as_user='lje5u')
        workflow_api = self.get_workflow_api(workflow, user_uid='lje5u')
        first_task = workflow_api.next_task

        # lje5u has access to the first task
        self.assertEqual(None, first_task.lane)
        self.assertEqual('READY', first_task.state)

        # Complete the form as lje5u
        form_data = {'id': 1}
        workflow_api = self.complete_form(workflow, first_task, form_data, user_uid='lje5u')
        second_task = workflow_api.next_task

        # lje5u does *not* have access to the second task
        self.assertEqual('Reviewer', second_task.lane)
        self.assertEqual('LOCKED', second_task.state)

        # Try completing the form as lje5u anyway
        form_data = {'case_id': 123,
                     'case_worker': 'Some Case Worker',
                     'notes': 'Private: Do Not Read'}
        # This results in 'permission_denied'
        workflow_api = self.complete_form(workflow, second_task, form_data,
                                          user_uid='lje5u',
                                          error_code='permission_denied')
        # And workflow_api is None
        self.assertIsNone(workflow_api)

        # Note that lb3dp is in the Reviewer list
        self.assertEqual(['lb3dp'], second_task.data['Reviewer'])

        # Complete the form as lb3dp
        workflow_api = self.complete_form(workflow, second_task, form_data,
                                          user_uid='lb3dp')
        third_task = workflow_api.next_task

        # lb3dp does *not* have access to the third task
        self.assertEqual(None, third_task.lane)
        self.assertEqual('LOCKED', third_task.state)

        # Try it anyway
        workflow_api = self.complete_form(workflow, third_task, {},
                                          user_uid='lb3dp',
                                          error_code='permission_denied')
        self.assertIsNone(workflow_api)

        # Admin accounts do not override task permission, still denied
        workflow_api = self.complete_form(workflow, third_task, {},
                                          user_uid='dhf8r',
                                          error_code='permission_denied')
        self.assertIsNone(workflow_api)
        self.assertTrue(UserService.user_is_admin())

        # Complete the workflow as lje5u
        workflow_api = self.complete_form(workflow, third_task, {},
                                          user_uid='lje5u')
        self.assertEqual('End Event', workflow_api.next_task.type)
        self.assertEqual('COMPLETED', workflow_api.next_task.state)
