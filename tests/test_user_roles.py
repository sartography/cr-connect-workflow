import json

from tests.base_test import BaseTest
from crc.models.workflow import WorkflowStatus
from crc import db
from crc.api.common import ApiError
from crc.models.task_event import TaskEventModel, TaskEventSchema
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
                                    error_code="permission_denied")

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
        data["approval"] = True
        result = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid,
                                    error_code="permission_denied")

        # Only her supervisor can do that.
        self.complete_form(workflow, workflow_api.next_task, data, user_uid=supervisor.uid)

    def test_nav_includes_lanes(self):
        submitter = self.create_user(uid='lje5u')
        workflow = self.create_workflow('roles', as_user=submitter.uid)
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)

        nav = workflow_api.navigation
        self.assertEquals(5, len(nav))
        self.assertEquals("supervisor", nav[1]['lane'])

    def test_get_outstanding_tasks_awaiting_current_user(self):
        submitter = self.create_user(uid='lje5u')
        supervisor = self.create_user(uid='lb3dp')
        workflow = self.create_workflow('roles', as_user=submitter.uid)
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)

        # User lje5u can complete the first task, and set her supervisor
        data = workflow_api.next_task.data
        data['supervisor'] = supervisor.uid
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)

        # At this point there should be a task_log with an action of Lane Change on it for
        # the supervisor.
        task_logs = db.session.query(TaskEventModel). \
            filter(TaskEventModel.user_uid == supervisor.uid). \
            filter(TaskEventModel.action == WorkflowService.TASK_ACTION_ASSIGNMENT).all()
        self.assertEquals(1, len(task_logs))

        # A call to the /task endpoint as the supervisor user should return a list of
        # tasks that need their attention.
        rv = self.app.get('/v1.0/task_events?action=ASSIGNMENT',
                          headers=self.logged_in_headers(supervisor),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        tasks = TaskEventSchema(many=True).load(json_data)
        self.assertEquals(1, len(tasks))
        self.assertEquals(workflow.id, tasks[0]['workflow']['id'])
        self.assertEquals(workflow.study.id, tasks[0]['study']['id'])

        # Assure we can say something sensible like:
        # You have a task called "Approval" to be completed in the "Supervisor Approval" workflow
        # for the study 'Why dogs are stinky' managed by user "Jane Smith (js42x)",
        # please check here to complete the task.
        # Display name isn't set in the tests, so just checking name, but the full workflow details are included.
        # I didn't delve into the full user details to keep things decoupled from ldap, so you just get the
        # uid back, but could query to get the full entry.
        self.assertEquals("roles", tasks[0]['workflow']['name'])
        self.assertEquals("Beer consumption in the bipedal software engineer", tasks[0]['study']['title'])
        self.assertEquals("lje5u", tasks[0]['study']['user_uid'])

        # Completing the next step of the workflow will close the task.
        data['approval'] = True
        self.complete_form(workflow, workflow_api.next_task, data, user_uid=supervisor.uid)

    def test_navigation_and_current_task_updates_through_workflow(self):

        submitter = self.create_user(uid='lje5u')
        supervisor = self.create_user(uid='lb3dp')
        workflow = self.create_workflow('roles', as_user=submitter.uid)

        # Navigation as Submitter with ready task.
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)
        nav = workflow_api.navigation
        self.assertEquals(5, len(nav))
        self.assertEquals('READY', nav[0]['state'])  # First item is ready, no progress yet.
        self.assertEquals('LOCKED', nav[1]['state'])  # Second item is locked, it is the review and doesn't belong to this user.
        self.assertEquals('LOCKED', nav[2]['state'])  # third item is a gateway, and belongs to no one, and is locked.
        self.assertEquals('NOOP', nav[3]['state'])  # Approved Path, has no operation
        self.assertEquals('NOOP', nav[4]['state'])  # Rejected Path, has no operation.
        self.assertEquals('READY', workflow_api.next_task.state)

        # Navigation as Submitter after handoff to supervisor
        data = workflow_api.next_task.data
        data['supervisor'] = supervisor.uid
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)
        nav = workflow_api.navigation
        self.assertEquals('COMPLETED', nav[0]['state'])  # First item is ready, no progress yet.
        self.assertEquals('LOCKED', nav[1]['state'])  # Second item is locked, it is the review and doesn't belong to this user.
        self.assertEquals('LOCKED', nav[2]['state'])  # third item is a gateway, and belongs to no one, and is locked.
        self.assertEquals('LOCKED', workflow_api.next_task.state)
        # In the event the next task is locked, we should say something sensible here.
        # It is possible to look at the role of the task, and say The next task "TASK TITLE" will
        # be handled by 'dhf8r', who is full-filling the role of supervisor. the Task Data
        # is guaranteed to have a supervisor attribute in it that will contain the users uid, which
        # could be looked up through an ldap service.
        self.assertEquals('supervisor', workflow_api.next_task.lane)


        # Navigation as Supervisor
        workflow_api = self.get_workflow_api(workflow, user_uid=supervisor.uid)
        nav = workflow_api.navigation
        self.assertEquals(5, len(nav))
        self.assertEquals('LOCKED', nav[0]['state'])  # First item belongs to the submitter, and is locked.
        self.assertEquals('READY', nav[1]['state'])  # Second item is locked, it is the review and doesn't belong to this user.
        self.assertEquals('LOCKED', nav[2]['state'])  # third item is a gateway, and belongs to no one, and is locked.
        self.assertEquals('READY', workflow_api.next_task.state)

        data = workflow_api.next_task.data
        data["approval"] = False
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=supervisor.uid)

        # Navigation as Supervisor, after completing task.
        nav = workflow_api.navigation
        self.assertEquals(5, len(nav))
        self.assertEquals('LOCKED', nav[0]['state'])  # First item belongs to the submitter, and is locked.
        self.assertEquals('COMPLETED', nav[1]['state'])  # Second item is locked, it is the review and doesn't belong to this user.
        self.assertEquals('COMPLETED', nav[2]['state'])  # third item is a gateway, and is now complete.
        self.assertEquals('LOCKED', workflow_api.next_task.state)

        # Navigation as Submitter, coming back in to a rejected workflow to view the rejection message.
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)
        nav = workflow_api.navigation
        self.assertEquals(5, len(nav))
        self.assertEquals('COMPLETED', nav[0]['state'])  # First item belongs to the submitter, and is locked.
        self.assertEquals('LOCKED', nav[1]['state'])  # Second item is locked, it is the review and doesn't belong to this user.
        self.assertEquals('LOCKED', nav[2]['state'])  # third item is a gateway belonging to the supervisor, and is locked.
        self.assertEquals('READY', workflow_api.next_task.state)

        # Navigation as Submitter, re-completing the original request a second time, and sending it for review.
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)
        nav = workflow_api.navigation
        self.assertEquals(5, len(nav))
        self.assertEquals('READY', nav[0]['state'])  # When you loop back the task is again in the ready state.
        self.assertEquals('LOCKED', nav[1]['state'])  # Second item is locked, it is the review and doesn't belong to this user.
        self.assertEquals('LOCKED', nav[2]['state'])  # third item is a gateway belonging to the supervisor, and is locked.
        self.assertEquals('READY', workflow_api.next_task.state)

        data["favorite_color"] = "blue"
        data["quest"] = "to seek the holy grail"
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)
        self.assertEquals('LOCKED', workflow_api.next_task.state)

        workflow_api = self.get_workflow_api(workflow, user_uid=supervisor.uid)
        self.assertEquals('READY', workflow_api.next_task.state)

        data = workflow_api.next_task.data
        data["approval"] = True
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=supervisor.uid)
        self.assertEquals('LOCKED', workflow_api.next_task.state)

        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)
        self.assertEquals('COMPLETED', workflow_api.next_task.state)
        self.assertEquals('EndEvent', workflow_api.next_task.type) # Are are at the end.
        self.assertEquals(WorkflowStatus.complete, workflow_api.status)