import json
import random
from unittest.mock import patch

from tests.base_test import BaseTest

from crc import session, app
from crc.models.api_models import WorkflowApiSchema, MultiInstanceType
from crc.models.workflow import WorkflowStatus
from example_data import ExampleDataLoader


class TestMultiinstanceTasksApi(BaseTest):


    @patch('crc.services.protocol_builder.requests.get')
    def test_multi_instance_task(self, mock_get):

        ExampleDataLoader().load_reference_documents()

        # Enable the protocol builder.
        app.config['PB_ENABLED'] = True

        # This depends on getting a list of investigators back from the protocol builder.
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('investigators.json')

        workflow = self.create_workflow('multi_instance')

        # get the first form in the two form workflow.
        workflow_api = self.get_workflow_api(workflow)
        navigation = self.get_workflow_api(workflow_api).navigation
        self.assertEqual(5, len(navigation)) # Start task, form_task, multi_task, end task
        self.assertEqual("UserTask", workflow_api.next_task.type)
        self.assertEqual(MultiInstanceType.sequential.value, workflow_api.next_task.multi_instance_type)
        self.assertEqual(5, workflow_api.next_task.multi_instance_count)

        # Assure that the names for each task are properly updated, so they aren't all the same.
        self.assertEqual("Primary Investigator", workflow_api.next_task.title)


    @patch('crc.services.protocol_builder.requests.get')
    def test_parallel_multi_instance(self, mock_get):

        # Assure we get nine investigators back from the API Call, as set in the investigators.json file.
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('investigators.json')

        ExampleDataLoader().load_reference_documents()

        workflow = self.create_workflow('multi_instance_parallel')

        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual(9, len(workflow_api.navigation))
        ready_items = [nav for nav in workflow_api.navigation if nav.state == "READY"]
        self.assertEqual(5, len(ready_items))

        self.assertEqual("UserTask", workflow_api.next_task.type)
        self.assertEqual("MultiInstanceTask",workflow_api.next_task.name)
        self.assertEqual("Primary Investigator", workflow_api.next_task.title)

        for i in random.sample(range(5), 5):
            task_id = ready_items[i].task_id
            rv = self.app.put('/v1.0/workflow/%i/task/%s/set_token' % (workflow.id, task_id),
                              headers=self.logged_in_headers(),
                              content_type="application/json")
            self.assert_success(rv)
            json_data = json.loads(rv.get_data(as_text=True))
            workflow_api = WorkflowApiSchema().load(json_data)
            data = workflow_api.next_task.data
            data['investigator']['email'] = "dhf8r@virginia.edu"
            self.complete_form(workflow, workflow_api.next_task, data)
            #tasks = self.get_workflow_api(workflow).user_tasks

        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual(WorkflowStatus.complete, workflow_api.status)


    @patch('crc.services.protocol_builder.requests.get')
    def test_parallel_multi_instance_update_all(self, mock_get):

        # Assure we get nine investigators back from the API Call, as set in the investigators.json file.
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('investigators.json')

        ExampleDataLoader().load_reference_documents()

        workflow = self.create_workflow('multi_instance_parallel')

        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual(9, len(workflow_api.navigation))
        ready_items = [nav for nav in workflow_api.navigation if nav.state == "READY"]
        self.assertEqual(5, len(ready_items))

        self.assertEqual("UserTask", workflow_api.next_task.type)
        self.assertEqual("MultiInstanceTask",workflow_api.next_task.name)
        self.assertEqual("Primary Investigator", workflow_api.next_task.title)

        data = workflow_api.next_task.data
        data['investigator']['email'] = "dhf8r@virginia.edu"
        self.complete_form(workflow, workflow_api.next_task, data, update_all=True)

        workflow = self.get_workflow_api(workflow)
        self.assertEqual(WorkflowStatus.complete, workflow.status)
        data = workflow.next_task.data
        for key in data["StudyInfo"]["investigators"]:
            self.assertEqual("dhf8r@virginia.edu", data["StudyInfo"]["investigators"][key]['email'])


