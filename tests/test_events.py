import json

from tests.base_test import BaseTest
from crc.models.workflow import WorkflowStatus
from crc import db
from flask_bpmn.api.api_error import ApiError
from crc.models.task_event import TaskEventModel, TaskEventSchema
from crc.services.workflow_service import WorkflowService


class TestEvents(BaseTest):


    def test_list_events_by_workflow(self):
        workflow_one = self.create_workflow('exclusive_gateway')

        # Start a the workflow.
        first_task = self.get_workflow_api(workflow_one).next_task
        self.complete_form(workflow_one, first_task, {"has_bananas": True})
        workflow_one = self.get_workflow_api(workflow_one)
        self.assertEqual('Task_Num_Bananas', workflow_one.next_task.name)

        # Start a second workflow
        workflow_two = self.create_workflow('subprocess')
        workflow_api_two = self.get_workflow_api(workflow_two)

        # Get all action events across workflows
        rv = self.app.get('/v1.0/task_events?action=ASSIGNMENT',
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        tasks = TaskEventSchema(many=True).load(json_data)
        self.assertEqual(2, len(tasks))

        # Get action events for a single workflow
        rv = self.app.get(f'/v1.0/task_events?action=ASSIGNMENT&workflow={workflow_one.id}',
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        tasks = TaskEventSchema(many=True).load(json_data)
        self.assertEqual(1, len(tasks))
