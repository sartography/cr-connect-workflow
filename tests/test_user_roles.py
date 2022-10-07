import json

from tests.base_test import BaseTest

from crc.models.api_models import NavigationItemSchema
from crc.models.workflow import WorkflowStatus
from crc import db
from crc.api.common import ApiError
from crc.models.task_event import TaskEventModel, TaskEventSchema, TaskAction
from crc.services.workflow_service import WorkflowService


class TestUserRoles(BaseTest):

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
        self.assertEqual("invalid_role", error.code)

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
        self.assertEqual(3, len(nav))
        self.assertEqual("supervisor", nav[2].lane)

    def test_get_outstanding_tasks_awaiting_current_user(self):
        submitter = self.create_user(uid='lje5u')
        supervisor = self.create_user(uid='lb3dp')
        workflow = self.create_workflow('roles', display_name="Roles", as_user=submitter.uid)
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)

        # User lje5u can complete the first task, and set her supervisor
        data = workflow_api.next_task.data
        data['supervisor'] = supervisor.uid
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)

        # At this point there should be a task_log with an action of Lane Change on it for
        # the supervisor.
        task_logs = db.session.query(TaskEventModel). \
            filter(TaskEventModel.user_uid == supervisor.uid). \
            filter(TaskEventModel.action == TaskAction.ASSIGNMENT.value).all()
        self.assertEqual(1, len(task_logs))

        # A call to the /task endpoint as the supervisor user should return a list of
        # tasks that need their attention.
        rv = self.app.get('/v1.0/task_events?action=ASSIGNMENT',
                          headers=self.logged_in_headers(supervisor),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        tasks = TaskEventSchema(many=True).load(json_data)
        self.assertEqual(1, len(tasks))
        self.assertEqual(workflow.id, tasks[0]['workflow']['id'])
        self.assertEqual(workflow.study.id, tasks[0]['study']['id'])
        self.assertEqual("Test Workflows", tasks[0]['workflow']['category_display_name'])

        # Assure we can say something sensible like:
        # You have a task called "Approval" to be completed in the "Supervisor Approval" workflow
        # for the study 'Why dogs are stinky' managed by user "Jane Smith (js42x)",
        # please check here to complete the task.
        # Just checking display_name for workflow, but the full workflow details are included.
        # I didn't delve into the full user details to keep things decoupled from ldap, so you just get the
        # uid back, but could query to get the full entry.
        self.assertEqual("Roles", tasks[0]['workflow']['display_name'])
        self.assertEqual("Beer consumption in the bipedal software engineer", tasks[0]['study']['title'])
        self.assertEqual("lje5u", tasks[0]['study']['user_uid'])

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
        self.assertEqual(3, len(nav))
        self.assertEqual('READY', nav[1].state)  # First item is ready, no progress yet.
        self.assertEqual('LOCKED', nav[2].state)  # Second item is locked, it is the review and doesn't belong to this user.
        self.assertEqual('READY', workflow_api.next_task.state)

        # Navigation as Submitter after handoff to supervisor
        data = workflow_api.next_task.data
        data['supervisor'] = supervisor.uid
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)
        nav = workflow_api.navigation
        self.assertEqual('COMPLETED', nav[1].state)  # First item is ready, no progress yet.
        self.assertEqual('LOCKED', nav[2].state)  # Second item is locked, it is the review and doesn't belong to this user.
        # In the event the next task is locked, we should say something sensible here.
        # It is possible to look at the role of the task, and say The next task "TASK TITLE" will
        # be handled by 'dhf8r', who is full-filling the role of supervisor. the Task Data
        # is guaranteed to have a supervisor attribute in it that will contain the users uid, which
        # could be looked up through an ldap service.
        self.assertEqual('supervisor', workflow_api.next_task.lane)


        # Navigation as Supervisor
        workflow_api = self.get_workflow_api(workflow, user_uid=supervisor.uid)
        nav = workflow_api.navigation
        self.assertEqual('LOCKED', nav[1].state)  # First item belongs to the submitter, and is locked.
        self.assertEqual('READY', nav[2].state)  # Second item is ready, as we are now the supervisor.
        self.assertEqual('READY', workflow_api.next_task.state)

        data = workflow_api.next_task.data
        data["approval"] = False
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=supervisor.uid)

        # Navigation as Supervisor, after completing task.
        nav = workflow_api.navigation
        self.assertEqual('LOCKED', nav[1].state)  # First item belongs to the submitter, and is locked.
        self.assertEqual('COMPLETED', nav[2].state)  # Second item is locked, it is the review and doesn't belong to this user.

        # Navigation as Submitter, coming back in to a rejected workflow to view the rejection message.
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)
        nav = workflow_api.navigation
        self.assertEqual(4, len(nav))
        self.assertEqual('COMPLETED', nav[1].state)  # First item belongs to the submitter, and is locked.
        self.assertEqual('LOCKED', nav[2].state)  # Second item is locked, it is the review and doesn't belong to this user.
        self.assertEqual('READY', nav[3].state)

        # Navigation as Submitter, re-completing the original request a second time, and sending it for review.
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)
        nav = workflow_api.navigation
        self.assertEqual('READY', nav[1].state)  # When you loop back the task is again in the ready state.
        self.assertEqual('LOCKED', nav[2].state)  # Second item is locked, it is the review and doesn't belong to this user.
        self.assertEqual('READY', workflow_api.next_task.state)

        data["favorite_color"] = "blue"
        data["quest"] = "to seek the holy grail"
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)
        self.assertEqual('LOCKED', workflow_api.next_task.state)

        workflow_api = self.get_workflow_api(workflow, user_uid=supervisor.uid)
        self.assertEqual('READY', workflow_api.next_task.state)

        data = workflow_api.next_task.data
        data["approval"] = True
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=supervisor.uid)
        self.assertEqual('LOCKED', workflow_api.next_task.state)

        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)
        self.assertEqual('COMPLETED', workflow_api.next_task.state)
        self.assertEqual('End Event', workflow_api.next_task.type) # Are are at the end.
        self.assertEqual(WorkflowStatus.complete, workflow_api.status)

    def get_assignment_task_events(self, uid):
        return db.session.query(TaskEventModel). \
            filter(TaskEventModel.user_uid == uid). \
            filter(TaskEventModel.action == TaskAction.ASSIGNMENT.value).all()

    def test_workflow_reset_correctly_resets_the_task_events(self):

        submitter = self.create_user(uid='lje5u')
        supervisor = self.create_user(uid='lb3dp')
        workflow = self.create_workflow('roles', display_name="Roles", as_user=submitter.uid)
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)

        # User lje5u can complete the first task, and set her supervisor
        data = workflow_api.next_task.data
        data['supervisor'] = supervisor.uid
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)

        # At this point there should be a task_log with an action of ASSIGNMENT on it for
        # the supervisor.
        self.assertEqual(1, len(self.get_assignment_task_events(supervisor.uid)))

        # Resetting the workflow at this point should clear the event log.
        workflow_api = self.restart_workflow_api(workflow, user_uid=submitter.uid)
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)
        self.assertEqual(0, len(self.get_assignment_task_events(supervisor.uid)))

        # Re-complete first task, and awaiting tasks should shift to 0 for for submitter, and 1 for supervisor
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)
        self.assertEqual(0, len(self.get_assignment_task_events(submitter.uid)))
        self.assertEqual(1, len(self.get_assignment_task_events(supervisor.uid)))

        # Complete the supervisor task with rejected approval, and the assignments should switch.
        workflow_api = self.get_workflow_api(workflow, user_uid=supervisor.uid)
        data = workflow_api.next_task.data
        data["approval"] = False
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=supervisor.uid)
        self.assertEqual(1, len(self.get_assignment_task_events(submitter.uid)))
        self.assertEqual(0, len(self.get_assignment_task_events(supervisor.uid)))

        # Mark the return form review page as complete, and then recomplete the form, and assignments switch yet again.
        workflow_api = self.get_workflow_api(workflow, user_uid=submitter.uid)
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)
        self.assertEqual(0, len(self.get_assignment_task_events(submitter.uid)))
        self.assertEqual(1, len(self.get_assignment_task_events(supervisor.uid)))

        # Complete the supervisor task, accepting the approval, and the workflow is completed.
        # When it is all done, there should be no outstanding assignments.
        workflow_api = self.get_workflow_api(workflow, user_uid=supervisor.uid)
        data = workflow_api.next_task.data
        data["approval"] = True
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=supervisor.uid)
        self.assertEqual(WorkflowStatus.complete, workflow_api.status)
        self.assertEqual('End Event', workflow_api.next_task.type) # Are are at the end.
        self.assertEqual(0, len(self.get_assignment_task_events(submitter.uid)))
        self.assertEqual(0, len(self.get_assignment_task_events(supervisor.uid)))

        # Sending any subsequent complete forms does not result in a new task event
        with self.assertRaises(AssertionError) as _api_error:
            workflow_api = self.complete_form(workflow, workflow_api.next_task, data, user_uid=submitter.uid)

        self.assertEqual(0, len(self.get_assignment_task_events(submitter.uid)))
        self.assertEqual(0, len(self.get_assignment_task_events(supervisor.uid)))

    def test_no_error_when_calling_end_loop_on_non_looping_task(self):

        workflow = self.create_workflow('hello_world')
        workflow_api = self.get_workflow_api(workflow)

        data = workflow_api.next_task.data
        data['name'] = "john"
        workflow_api = self.complete_form(workflow, workflow_api.next_task, data, terminate_loop=True)
