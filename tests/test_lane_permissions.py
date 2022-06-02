from tests.base_test import BaseTest

from flask import g

from crc.services.user_service import UserService


class TestLanePermissions(BaseTest):
    """Can users access tasks appropriately in lanes.
       Can users access Start Over appropriately in lanes
       Can admins override appropriately"""

    def test_can_has_permissions(self):
        self.add_users()
        self.create_user(uid="lje5u", email="test_user@example.com", display_name="Test User")
        # g.user = 'lje5u'

        workflow = self.create_workflow('lane_permissions', as_user='lje5u')
        workflow_api = self.get_workflow_api(workflow, user_uid='lje5u')
        task = workflow_api.next_task

        form_data = {'id': 1}
        workflow_api = self.complete_form(workflow, task, form_data, user_uid='lje5u')
        task = workflow_api.next_task

        form_data = {'case_id': 123,
                     'case_worker': 'Some Case Worker',
                     'notes': 'Private: Do Not Read'}
        workflow_api = self.complete_form(workflow, task, form_data,
                                          user_uid='lje5u',
                                          error_code='permission_denied')
        self.assertIsNone(workflow_api)

        workflow_api = self.complete_form(workflow, task, form_data,
                                          user_uid='lb3dp')

        print('test_can_has_permissions')


# if isinstance(spiff_task.task_spec, StartEvent) and nav_item.lane:
#     in_list = UserService.in_list(user_uids, allow_admin_impersonate=True)
#     impersonator_is_admin = UserService.user_is_admin(allow_admin_impersonate=True)
#     if not in_list and not impersonator_is_admin:
