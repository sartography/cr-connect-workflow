from tests.base_test import BaseTest

from crc import session
from crc.models.task_event import TaskEventSchema
from crc.models.workflow import WorkflowModel
from crc.services.workflow_processor import WorkflowProcessor
from crc import app
from unittest.mock import patch
import os
import json


class TestUpdateStaleTaskEvents(BaseTest):
    """This test does not test whether we remove stale approvals. It only test the logic of the script.
    What I need to do, is mock the results of study_info['documents'] and
    set an approval test to True and check Approvals, and then
    set the approval test to False and check the Approvals again.
    But, I'd also like to test for all known Approval types. I.e., Pharmacy, Radiology, etc."""

    def get_workflow_events(self, workflow_id):
        rv = self.app.get(f'/v1.0/task_events?action=ASSIGNMENT&workflow={workflow_id}',
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        task_events = TaskEventSchema(many=True).load(json_data)
        return task_events

    def test_update_stale_approvals(self):
        """At each Manual Task, we check the ASSIGNMENT task events and (sometimes) task data. """

        self.add_users()  # adds users in test ldap
        self.create_reference_document()  # adds documents.xlsx to tests/SPECS/Reference Files/

        workflow = self.create_workflow('update_stale_approvals')


        #
        # Manual Task: Review Parameters
        #
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        assert task.name == 'Activity_ReviewBeforeForm'
        assert task.data == {'Approvers': ['kcm4zc', 'lb3dp']}

        # We should have one ASSIGNMENT event, for the study owner
        task_events = self.get_workflow_events(workflow.id)
        assert len(task_events) == 1
        assert task_events[0]['user_uid'] == 'dhf8r'

        self.complete_form(workflow, task, {})

        #
        # User Task: Display Approver Form
        #
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        assert task.name == 'Activity_DisplayApproverForm'

        # Two events, for the approvers
        task_events = self.get_workflow_events(workflow.id)
        assert len(task_events) == 2
        for task_event in task_events:
            assert task_event['user_uid'] in ['kcm4zc', 'lb3dp']
            assert task_event['task_name'] == 'Activity_DisplayApproverForm'

        self.complete_form(workflow, task, {'approver_response': 'yes', 'comment': 'Looks good!'}, user_uid='kcm4zc')

        #
        # Manual Task: Review After Form
        #
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        assert task.name == 'Activity_ReviewAfterForm'

        assert task.data == {'Approvers': ['kcm4zc', 'lb3dp'], 'approver_response': 'yes', 'comment': 'Looks good!'}

        # Two events, for the approvers
        task_events = self.get_workflow_events(workflow.id)
        assert len(task_events) == 2
        for task_event in task_events:
            assert task_event['user_uid'] in ['kcm4zc', 'lb3dp']
            assert task_event['task_name'] == 'Activity_ReviewAfterForm'

        self.complete_form(workflow, task, {}, user_uid='kcm4zc')

        #
        # Manual Task: Review Before Update
        #
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        assert task.name == 'Activity_ReviewBeforeUpdate'

        # One event, for the study owner
        task_events = self.get_workflow_events(workflow.id)
        assert len(task_events) == 1

        assert task_events[0]['user_uid'] == 'dhf8r'
        assert task_events[0]['task_name'] == 'Activity_ReviewBeforeUpdate'

        self.complete_form(workflow, task, {})

        #
        # Manual Task: Review After Update
        #
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        assert task.name == 'Activity_ReviewAfterUpdate'

        # One event, for the study owner
        task_events = self.get_workflow_events(workflow.id)
        assert len(task_events) == 1

        assert task_events[0]['user_uid'] == 'dhf8r'
        assert task_events[0]['task_name'] == 'Activity_ReviewAfterUpdate'

        self.complete_form(workflow, task, {})

        #
        # End Event
        #
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        assert task.type == 'End Event'

        # No events - Workflow complete
        task_events = self.get_workflow_events(workflow.id)
        assert len(task_events) == 0
