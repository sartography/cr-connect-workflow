import json
import os
from unittest.mock import patch

from crc import session, app
from crc.models.api_models import WorkflowApiSchema, MultiInstanceType, TaskSchema
from crc.models.file import FileModelSchema
from crc.models.stats import TaskEventModel
from crc.models.workflow import WorkflowStatus
from crc.services.workflow_service import WorkflowService
from tests.base_test import BaseTest


class TestTasksApi(BaseTest):

    def get_workflow_api(self, workflow, soft_reset=False, hard_reset=False):
        rv = self.app.get('/v1.0/workflow/%i?soft_reset=%s&hard_reset=%s' %
                          (workflow.id, str(soft_reset), str(hard_reset)),
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        workflow_api = WorkflowApiSchema().load(json_data)
        self.assertEqual(workflow.workflow_spec_id, workflow_api.workflow_spec_id)
        return workflow_api

    def complete_form(self, workflow_in, task_in, dict_data, error_code = None):
        prev_completed_task_count = workflow_in.completed_tasks
        if isinstance(task_in, dict):
            task_id = task_in["id"]
        else:
            task_id = task_in.id
        rv = self.app.put('/v1.0/workflow/%i/task/%s/data' % (workflow_in.id, task_id),
                          headers=self.logged_in_headers(),
                          content_type="application/json",
                          data=json.dumps(dict_data))
        if error_code:
            self.assert_failure(rv, error_code=error_code)
            return

        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))

        # Assure stats are updated on the model
        workflow = WorkflowApiSchema().load(json_data)
        # The total number of tasks may change over time, as users move through gateways
        # branches may be pruned. As we hit parallel Multi-Instance new tasks may be created...
        self.assertIsNotNone(workflow.total_tasks)
        self.assertEquals(prev_completed_task_count + 1, workflow.completed_tasks)
        # Assure a record exists in the Task Events
        task_events = session.query(TaskEventModel) \
            .filter_by(workflow_id=workflow.id) \
            .filter_by(task_id=task_id) \
            .order_by(TaskEventModel.date.desc()).all()
        self.assertGreater(len(task_events), 0)
        event = task_events[0]
        self.assertIsNotNone(event.study_id)
        self.assertEquals("dhf8r", event.user_uid)
        self.assertEquals(workflow.id, event.workflow_id)
        self.assertEquals(workflow.workflow_spec_id, event.workflow_spec_id)
        self.assertEquals(workflow.spec_version, event.spec_version)
        self.assertEquals(WorkflowService.TASK_ACTION_COMPLETE, event.action)
        self.assertEquals(task_in.id, task_id)
        self.assertEquals(task_in.name, event.task_name)
        self.assertEquals(task_in.title, event.task_title)
        self.assertEquals(task_in.type, event.task_type)
        self.assertEquals("COMPLETED", event.task_state)
        self.assertEquals(task_in.mi_type.value, event.mi_type)
        self.assertEquals(task_in.mi_count, event.mi_count)
        self.assertEquals(task_in.mi_index, event.mi_index)
        self.assertEquals(task_in.process_name, event.process_name)
        self.assertIsNotNone(event.date)


        workflow = WorkflowApiSchema().load(json_data)
        return workflow


    def test_get_current_user_tasks(self):
        self.load_example_data()
        workflow = self.create_workflow('random_fact')
        tasks = self.get_workflow_api(workflow).user_tasks
        self.assertEqual("Task_User_Select_Type", tasks[0].name)
        self.assertEqual(3, len(tasks[0].form["fields"][0]["options"]))
        self.assertIsNotNone(tasks[0].documentation)
        expected_docs = """# h1 Heading 8-)
## h2 Heading
### h3 Heading
#### h4 Heading
##### h5 Heading
###### h6 Heading
"""
        self.assertTrue(str.startswith(tasks[0].documentation, expected_docs))

    def test_two_forms_task(self):
        # Set up a new workflow
        self.load_example_data()
        workflow = self.create_workflow('two_forms')
        # get the first form in the two form workflow.
        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual('two_forms', workflow_api.workflow_spec_id)
        self.assertEqual(2, len(workflow_api.user_tasks))
        self.assertIsNotNone(workflow_api.user_tasks[0].form)
        self.assertEqual("UserTask", workflow_api.next_task['type'])
        self.assertEqual("StepOne", workflow_api.next_task['name'])
        self.assertEqual(1, len(workflow_api.next_task['form']['fields']))

        # Complete the form for Step one and post it.
        self.complete_form(workflow, workflow_api.user_tasks[0], {"color": "blue"})

        # Get the next Task
        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual("StepTwo", workflow_api.next_task['name'])

        # Get all user Tasks and check that the data have been saved
        for task in workflow_api.user_tasks:
            self.assertIsNotNone(task.data)
            for val in task.data.values():
                self.assertIsNotNone(val)

    def test_error_message_on_bad_gateway_expression(self):
        self.load_example_data()
        workflow = self.create_workflow('exclusive_gateway')

        # get the first form in the two form workflow.
        tasks = self.get_workflow_api(workflow).user_tasks
        self.complete_form(workflow, tasks[0], {"has_bananas": True})

    def test_workflow_with_parallel_forms(self):
        self.load_example_data()
        workflow = self.create_workflow('exclusive_gateway')

        # get the first form in the two form workflow.
        tasks = self.get_workflow_api(workflow).user_tasks
        self.complete_form(workflow, tasks[0], {"has_bananas": True})

        # Get the next Task
        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual("Task_Num_Bananas", workflow_api.next_task['name'])

    def test_get_workflow_contains_details_about_last_task_data(self):
        self.load_example_data()
        workflow = self.create_workflow('exclusive_gateway')

        # get the first form in the two form workflow.
        tasks = self.get_workflow_api(workflow).user_tasks
        workflow_api = self.complete_form(workflow, tasks[0], {"has_bananas": True})

        self.assertIsNotNone(workflow_api.last_task)
        self.assertEqual({"has_bananas": True}, workflow_api.last_task['data'])

    def test_get_workflow_contains_reference_to_last_task_and_next_task(self):
        self.load_example_data()
        workflow = self.create_workflow('exclusive_gateway')

        # get the first form in the two form workflow.
        tasks = self.get_workflow_api(workflow).user_tasks
        self.complete_form(workflow, tasks[0], {"has_bananas": True})

        workflow_api = self.get_workflow_api(workflow)
        self.assertIsNotNone(workflow_api.last_task)
        self.assertIsNotNone(workflow_api.next_task)


    def test_document_added_to_workflow_shows_up_in_file_list(self):
        self.load_example_data()
        self.create_reference_document()
        workflow = self.create_workflow('docx')
        # get the first form in the two form workflow.
        tasks = self.get_workflow_api(workflow).user_tasks
        data = {
            "full_name": "Buck of the Wild",
            "date": "5/1/2020",
            "title": "Leader of the Pack",
            "company": "In the company of wolves",
            "last_name": "Mr. Wolf"
        }
        workflow_api = self.complete_form(workflow, tasks[0], data)
        self.assertIsNotNone(workflow_api.next_task)
        self.assertEqual("EndEvent_0evb22x", workflow_api.next_task['name'])
        self.assertTrue(workflow_api.status == WorkflowStatus.complete)
        rv = self.app.get('/v1.0/file?workflow_id=%i' % workflow.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        files = FileModelSchema(many=True).load(json_data, session=session)
        self.assertTrue(len(files) == 1)
        # Assure we can still delete the study even when there is a file attached to a workflow.
        rv = self.app.delete('/v1.0/study/%i' % workflow.study_id, headers=self.logged_in_headers())
        self.assert_success(rv)



    def test_get_documentation_populated_in_end(self):
        self.load_example_data()
        workflow = self.create_workflow('random_fact')
        workflow_api = self.get_workflow_api(workflow)
        tasks = workflow_api.user_tasks
        self.assertEqual("Task_User_Select_Type", tasks[0].name)
        self.assertEqual(3, len(tasks[0].form["fields"][0]["options"]))
        self.assertIsNotNone(tasks[0].documentation)
        self.complete_form(workflow, workflow_api.user_tasks[0], {"type": "norris"})
        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual("EndEvent_0u1cgrf", workflow_api.next_task['name'])
        self.assertIsNotNone(workflow_api.next_task['documentation'])
        self.assertTrue("norris" in workflow_api.next_task['documentation'])

    def test_load_workflow_from_outdated_spec(self):

        # Start the basic two_forms workflow and complete a task.
        self.load_example_data()
        workflow = self.create_workflow('two_forms')
        workflow_api = self.get_workflow_api(workflow)
        self.complete_form(workflow, workflow_api.user_tasks[0], {"color": "blue"})
        self.assertTrue(workflow_api.is_latest_spec)

        # Modify the specification, with a major change that alters the flow and can't be deserialized
        # effectively, if it uses the latest spec files.
        file_path = os.path.join(app.root_path, '..', 'tests', 'data', 'two_forms', 'mods', 'two_forms_struc_mod.bpmn')
        self.replace_file("two_forms.bpmn", file_path)

        workflow_api = self.get_workflow_api(workflow)
        self.assertTrue(workflow_api.spec_version.startswith("v1 "))
        self.assertFalse(workflow_api.is_latest_spec)

        workflow_api = self.get_workflow_api(workflow, hard_reset=True)
        self.assertTrue(workflow_api.spec_version.startswith("v2 "))
        self.assertTrue(workflow_api.is_latest_spec)

        # Assure this hard_reset sticks (added this after a bug was found)
        workflow_api = self.get_workflow_api(workflow)
        self.assertTrue(workflow_api.spec_version.startswith("v2 "))
        self.assertTrue(workflow_api.is_latest_spec)

    def test_soft_reset_errors_out_and_next_result_is_on_original_version(self):

        # Start the basic two_forms workflow and complete a task.
        self.load_example_data()
        workflow = self.create_workflow('two_forms')
        workflow_api = self.get_workflow_api(workflow)
        self.complete_form(workflow, workflow_api.user_tasks[0], {"color": "blue"})
        self.assertTrue(workflow_api.is_latest_spec)

        # Modify the specification, with a major change that alters the flow and can't be deserialized
        # effectively, if it uses the latest spec files.
        file_path = os.path.join(app.root_path, '..', 'tests', 'data', 'two_forms', 'mods', 'two_forms_struc_mod.bpmn')
        self.replace_file("two_forms.bpmn", file_path)

        # perform a soft reset returns an error
        rv = self.app.get('/v1.0/workflow/%i?soft_reset=%s&hard_reset=%s' %
                          (workflow.id, "true", "false"),
                          content_type="application/json",
                          headers=self.logged_in_headers())
        self.assert_failure(rv, error_code="unexpected_workflow_structure")

        # Try again without a soft reset, and we are still ok, and on the original version.
        workflow_api = self.get_workflow_api(workflow)
        self.assertTrue(workflow_api.spec_version.startswith("v1 "))
        self.assertFalse(workflow_api.is_latest_spec)


    def test_manual_task_with_external_documentation(self):
        self.load_example_data()
        workflow = self.create_workflow('manual_task_with_external_documentation')

        # get the first form in the two form workflow.
        tasks = self.get_workflow_api(workflow).user_tasks
        workflow_api = self.complete_form(workflow, tasks[0], {"name": "Dan"})

        workflow = self.get_workflow_api(workflow)
        self.assertEquals('Task_Manual_One', workflow.next_task['name'])
        self.assertEquals('ManualTask', workflow_api.next_task['type'])
        self.assertTrue('Markdown' in workflow_api.next_task['documentation'])
        self.assertTrue('Dan' in workflow_api.next_task['documentation'])

    def test_bpmn_extension_properties_are_populated(self):
        self.load_example_data()
        workflow = self.create_workflow('manual_task_with_external_documentation')

        # get the first form in the two form workflow.
        tasks = self.get_workflow_api(workflow).user_tasks
        self.assertEquals("JustAKey", tasks[0].properties[0]['id'])
        self.assertEquals("JustAValue", tasks[0].properties[0]['value'])


    @patch('crc.services.protocol_builder.requests.get')
    def test_multi_instance_task(self, mock_get):
        # This depends on getting a list of investigators back from the protocol builder.
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('investigators.json')

        self.load_example_data()
        workflow = self.create_workflow('multi_instance')

        # get the first form in the two form workflow.
        tasks = self.get_workflow_api(workflow).user_tasks
        self.assertEquals(1, len(tasks))
        self.assertEquals("UserTask", tasks[0].type)
        self.assertEquals(MultiInstanceType.sequential, tasks[0].mi_type)
        self.assertEquals(3, tasks[0].mi_count)


    def test_lookup_endpoint_for_task_field_enumerations(self):
        self.load_example_data()
        workflow = self.create_workflow('enum_options_with_search')
        # get the first form in the two form workflow.
        tasks = self.get_workflow_api(workflow).user_tasks
        task = tasks[0]
        field_id = task.form['fields'][0]['id']
        rv = self.app.get('/v1.0/workflow/%i/task/%s/lookup/%s?query=%s&limit=5' %
                          (workflow.id, task.id, field_id, 'c'), # All records with a word that starts with 'c'
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        results = json.loads(rv.get_data(as_text=True))
        self.assertEqual(5, len(results))

    def test_sub_process(self):
        self.load_example_data()
        workflow = self.create_workflow('subprocess')

        tasks = self.get_workflow_api(workflow).user_tasks
        self.assertEquals(2, len(tasks))
        self.assertEquals("UserTask", tasks[0].type)
        self.assertEquals("Activity_A", tasks[0].name)
        self.assertEquals("My Sub Process", tasks[0].process_name)
        workflow_api = self.complete_form(workflow, tasks[0], {"name": "Dan"})
        task = TaskSchema().load(workflow_api.next_task)
        self.assertIsNotNone(task)

        self.assertEquals("Activity_B", task.name)
        self.assertEquals("Sub Workflow Example", task.process_name)
        workflow_api = self.complete_form(workflow, task, {"name": "Dan"})
        self.assertEquals(WorkflowStatus.complete, workflow_api.status)

    def test_update_task_resets_token(self):
        self.load_example_data()
        workflow = self.create_workflow('exclusive_gateway')

        # Start the workflow.
        tasks = self.get_workflow_api(workflow).user_tasks
        self.complete_form(workflow, tasks[0], {"has_bananas": True})
        workflow = self.get_workflow_api(workflow)
        self.assertEquals('Task_Num_Bananas', workflow.next_task['name'])

        # Trying to re-submit the initial task, and answer differently, should result in an error.
        self.complete_form(workflow, tasks[0], {"has_bananas": False}, error_code="invalid_state")

        # Go ahead and set the number of bananas.
        workflow = self.get_workflow_api(workflow)
        task = TaskSchema().load(workflow.next_task)

        self.complete_form(workflow, task, {"num_bananas": 4})
        # We are now at the end of the workflow.

        # Make the old task the current task.
        rv = self.app.put('/v1.0/workflow/%i/task/%s/set_token' % (workflow.id, tasks[0].id),
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        workflow = WorkflowApiSchema().load(json_data)

        # Assure the last task is the task we were on before the reset,
        # and the Next Task is the one we just reset the token to be on.
        self.assertEquals("Task_Has_Bananas", workflow.next_task['name'])
        self.assertEquals("End", workflow.last_task['name'])

        # Go ahead and get that workflow one more time, it should still be right.
        workflow = self.get_workflow_api(workflow)

        # Assure the last task is the task we were on before the reset,
        # and the Next Task is the one we just reset the token to be on.
        self.assertEquals("Task_Has_Bananas", workflow.next_task['name'])
        self.assertEquals("End", workflow.last_task['name'])

        # The next task should be a different value.
        self.complete_form(workflow, tasks[0], {"has_bananas": False})
        workflow = self.get_workflow_api(workflow)
        self.assertEquals('Task_Why_No_Bananas', workflow.next_task['name'])


    # def test_parent_task_set_on_tasks(self):
    #     self.load_example_data()
    #     workflow = self.create_workflow('exclusive_gateway')
    #
    #     # Start the workflow.
    #     workflow = self.get_workflow_api(workflow)
    #     self.assertEquals(None, workflow.previous_task)
    #     self.complete_form(workflow, workflow.next_task, {"has_bananas": True})
    #     workflow = self.get_workflow_api(workflow)
    #     self.assertEquals('Task_Num_Bananas', workflow.next_task['name'])
    #     self.assertEquals('has_bananas', workflow.previous_task['name'])
