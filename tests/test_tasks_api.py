import json
import os

from crc import session, app
from crc.models.api_models import WorkflowApiSchema
from crc.models.file import FileModelSchema
from crc.models.stats import WorkflowStatsModel, TaskEventModel
from crc.models.workflow import WorkflowStatus
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

    def complete_form(self, workflow, task, dict_data):
        rv = self.app.put('/v1.0/workflow/%i/task/%s/data' % (workflow.id, task.id),
                          headers=self.logged_in_headers(),
                          content_type="application/json",
                          data=json.dumps(dict_data))
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))

        num_stats = session.query(WorkflowStatsModel) \
            .filter_by(workflow_id=workflow.id) \
            .filter_by(workflow_spec_id=workflow.workflow_spec_id) \
            .count()
        self.assertGreater(num_stats, 0)

        num_task_events = session.query(TaskEventModel) \
            .filter_by(workflow_id=workflow.id) \
            .filter_by(task_id=task.id) \
            .count()
        self.assertGreater(num_task_events, 0)

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

    def test_get_workflow_stats(self):
        self.load_example_data()
        workflow = self.create_workflow('exclusive_gateway')

        response_before = self.app.get('/v1.0/workflow/%i/stats' % workflow.id,
                                       content_type="application/json",
                                       headers=self.logged_in_headers())
        self.assert_success(response_before)
        db_stats_before = session.query(WorkflowStatsModel).filter_by(workflow_id=workflow.id).first()
        self.assertIsNone(db_stats_before)

        # Start the workflow.
        tasks = self.get_workflow_api(workflow).user_tasks
        self.complete_form(workflow, tasks[0], {"has_bananas": True})

        response_after = self.app.get('/v1.0/workflow/%i/stats' % workflow.id,
                                      content_type="application/json",
                                      headers=self.logged_in_headers())
        self.assert_success(response_after)
        db_stats_after = session.query(WorkflowStatsModel).filter_by(workflow_id=workflow.id).first()
        self.assertIsNotNone(db_stats_after)
        self.assertGreater(db_stats_after.num_tasks_complete, 0)
        self.assertGreater(db_stats_after.num_tasks_incomplete, 0)
        self.assertGreater(db_stats_after.num_tasks_total, 0)
        self.assertEqual(db_stats_after.num_tasks_total,
                         db_stats_after.num_tasks_complete + db_stats_after.num_tasks_incomplete)

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
