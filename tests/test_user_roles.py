import json

from crc.models.api_models import WorkflowApiSchema
from crc.models.stats import TaskEventModel
from tests.base_test import BaseTest
from crc import db
from crc.api.common import ApiError
from crc.services.workflow_service import WorkflowService


class TestTasksApi(BaseTest):

    def test_raise_error_if_role_does_not_exist_in_data(self):
        workflow = self.create_workflow('roles', as_user="lje5u")
        workflow_api = self.get_workflow_api(workflow, user_uid="lje5u")
        data = workflow_api.next_task.data
        # User lje5u can complete the first task
        self.complete_form(workflow, workflow_api.next_task, data, user_uid="lje5u")

        # The next task is a supervisor task, and should raise an error if the role
        # information is not in the task data.
        workflow_api = self.get_workflow_api(workflow, user_uid="lje5u")
        data = workflow_api.next_task.data
        data["approved"] = True
        result = self.complete_form(workflow, workflow_api.next_task, data, user_uid="lje5u",
                                    error_code="invalid_role")

    def test_validation_of_workflow_fails_if_workflow_does_not_define_user_for_lane(self):
        error = None
        try:
            workflow = self.create_workflow('invalid_roles', as_user="lje5u")
            WorkflowService.test_spec(workflow.workflow_spec_id)
        except ApiError as ae:
            error = ae
        self.assertIsNotNone(error, "An error should be raised.")
        self.assertEquals("invalid_role", error.code)

    def test_raise_error_if_user_does_not_have_the_correct_role(self):
        submitter = self.create_user(uid='lje5u')
        supervisor = self.create_user(uid='lb3dp')
        workflow = self.create_workflow('roles', as_user=submitter.uid)
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)

        # User lje5u can complete the first task, and set her supervisor
        data = workflow_api.next_task.data
        data['supervisor'] = supervisor.uid
        self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)

        # But she can not complete the supervisor role.
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)
        data = workflow_api.next_task.data
        data["approved"] = True
        result = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid,
                                    error_code="role_permission")

        # Only her supervisor can do that.
        self.complete_form(workflow, workflow_api.next_task, data, user_uid=supervisor.uid)

    def test_nav_includes_lanes(self):
        self.load_example_data()

        submitter = self.create_user(uid='lje5u')
        workflow = self.create_workflow('roles', as_user=submitter.uid)
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)

        nav = workflow_api.navigation
        self.assertEquals(5, len(nav))
        self.assertEquals("supervisor", nav[1]['lane'])

    def test_get_outstanding_tasks_awaiting_user_input(self):
        submitter = self.create_user(uid='lje5u')
        supervisor = self.create_user(uid='lb3dp')
        workflow = self.create_workflow('roles', as_user=submitter.uid)
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)

        # User lje5u can complete the first task, and set her supervisor
        data = workflow_api.next_task.data
        data['supervisor'] = supervisor.uid
        self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)

        # At this point there should be a task_log with an action of WAITING on it for
        # the supervisor.
        task_log = db.session.query(TaskEventModel).filter(TaskEventModel.user_uid == supervisor.uid)
        self.assertEquals(1, len(task_log))

        # A call to the /workflow endpoint as the supervisor user should return this workflow
        rv = self.app.get('/v1.0/workflow',
                          headers=self.logged_in_headers(supervisor.uid),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        workflow_api = WorkflowApiSchema().load(json_data)

        # The workflow navigation should be locked for all tasks that do not belong to the user.



        # Completing the next step of the workflow will close the task.
        self.complete_form(workflow, workflow_api.next_task, data, user_uid=supervisor.uid)


