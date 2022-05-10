import json
import os

from tests.base_test import BaseTest

from crc import session, app
from crc.models.api_models import WorkflowApiSchema
from crc.models.file import FileModelSchema
from crc.models.workflow import WorkflowModel, WorkflowState, WorkflowStatus
from crc.models.task_event import TaskEventModel


class TestTasksApi(BaseTest):

    def assert_options_populated(self, results, lookup_data_keys):
        for result in results:
            self.assertIsInstance(result, dict)
            for lookup_data_key in lookup_data_keys:
                self.assertTrue(lookup_data_key in result, 'should have all lookup data columns populated')

    def test_get_current_user_tasks(self):

        workflow = self.create_workflow('random_fact')
        workflow = self.get_workflow_api(workflow)
        task = workflow.next_task
        self.assertEqual("Task_User_Select_Type", task.name)
        self.assertEqual(3, len(task.form["fields"][0]["options"]))
        self.assertIsNotNone(task.documentation)
        expected_docs = """# h1 Heading 8-)
## h2 Heading
### h3 Heading
#### h4 Heading
##### h5 Heading
###### h6 Heading
"""
        self.assertTrue(str.startswith(task.documentation, expected_docs))

    def test_get_workflow_without_running_engine_steps(self):
        # Set up a new workflow
        workflow = self.create_workflow('two_forms')
        # get the first form in the two form workflow.
        workflow_api = self.get_workflow_api(workflow, do_engine_steps=False)

        # There should be no task event logs related to the workflow at this point.
        task_events = session.query(TaskEventModel).filter(TaskEventModel.workflow_id == workflow.id).all()
        self.assertEqual(0, len(task_events))

        # Since the workflow was not started, the call to read-only should not execute any engine steps the
        # current task should be the start event.
        self.assertEqual("Start", workflow_api.next_task.name)

    def test_get_form_for_previously_completed_task(self):
        """Assure we can look at previously completed steps without moving the token for the workflow."""


    def test_two_forms_task(self):
        # Set up a new workflow

        workflow = self.create_workflow('two_forms')
        # get the first form in the two form workflow.
        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual('two_forms', workflow_api.workflow_spec_id)
        self.assertEqual(5, len(workflow_api.navigation))
        self.assertIsNotNone(workflow_api.next_task.form)
        self.assertEqual("UserTask", workflow_api.next_task.type)
        self.assertEqual("StepOne", workflow_api.next_task.name)
        self.assertEqual(1, len(workflow_api.next_task.form['fields']))

        # Complete the form for Step one and post it.
        self.complete_form(workflow, workflow_api.next_task, {"color": "blue"})

        # Get the next Task
        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual("StepTwo", workflow_api.next_task.name)

        # Get all user Tasks and check that the data have been saved
        task = workflow_api.next_task
        self.assertIsNotNone(task.data)
        for val in task.data.values():
            self.assertIsNotNone(val)

    def test_error_message_on_bad_gateway_expression(self):
        workflow = self.create_workflow('exclusive_gateway')

        # get the first form in the two form workflow.
        task = self.get_workflow_api(workflow).next_task
        self.complete_form(workflow, task, {"has_bananas": True})

    def test_workflow_with_parallel_forms(self):
        workflow = self.create_workflow('exclusive_gateway')

        # get the first form in the two form workflow.
        task = self.get_workflow_api(workflow).next_task
        self.complete_form(workflow, task, {"has_bananas": True})

        # Get the next Task
        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual("Task_Num_Bananas", workflow_api.next_task.name)

    def test_navigation_with_parallel_forms(self):
        workflow = self.create_workflow('exclusive_gateway')

        # get the first form in the two form workflow.
        workflow_api = self.get_workflow_api(workflow)

        self.assertIsNotNone(workflow_api.navigation)
        nav = workflow_api.navigation
        self.assertEqual(4, len(nav))
        self.assertEqual("Do You Have Bananas", nav[1].description)
        self.assertEqual("Bananas?", nav[2].description)
        self.assertEqual("MAYBE", nav[2].state)

        self.assertEqual("yes", nav[2].children[0].description)
        self.assertEqual("MAYBE", nav[2].children[0].state)
        self.assertEqual("of Bananas", nav[2].children[0].children[0].description)
        self.assertEqual("EndEvent", nav[2].children[0].children[1].spec_type)

        self.assertEqual("no", nav[2].children[1].description)
        self.assertEqual("MAYBE", nav[2].children[1].state)
        self.assertEqual("no bananas", nav[2].children[1].children[0].description)
        self.assertEqual("EndEvent", nav[2].children[1].children[1].spec_type)

    def test_navigation_with_exclusive_gateway(self):
        workflow = self.create_workflow('exclusive_gateway_2')

        # get the first form in the two form workflow.
        workflow_api = self.get_workflow_api(workflow)
        self.assertIsNotNone(workflow_api.navigation)
        nav = workflow_api.navigation
        self.assertEqual(7, len(nav))
        self.assertEqual("Task 1", nav[1].description)
        self.assertEqual("Which Branch?", nav[2].description)
        self.assertEqual("a", nav[2].children[0].description)
        self.assertEqual("Task 2a", nav[2].children[0].children[0].description)
        self.assertEqual("b", nav[2].children[1].description)
        self.assertEqual("Task 2b", nav[2].children[1].children[0].description)
        self.assertEqual(None, nav[3].description)
        self.assertEqual("Task 3", nav[4].description)
        self.assertEqual("EndEvent", nav[5].spec_type)

    def test_document_added_to_workflow_shows_up_in_file_list(self):
        self.create_reference_document()
        workflow = self.create_workflow('docx')

        # get the first form in the two form workflow.
        task = self.get_workflow_api(workflow).next_task
        data = {
            "full_name": "Buck of the Wild",
            "date": "5/1/2020",
            "title": "Leader of the Pack",
            "company": "In the company of wolves",
            "last_name": "Mr. Wolf"
        }
        workflow_api = self.complete_form(workflow, task, data)
        self.assertIsNotNone(workflow_api.next_task)
        self.assertEqual("EndEvent_0evb22x", workflow_api.next_task.name)
        self.assertTrue(workflow_api.status == WorkflowStatus.complete)
        rv = self.app.get('/v1.0/file?workflow_id=%i' % workflow.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertTrue(len(json_data) == 1)

        # Assure we can still delete the study even when there is a file attached to a workflow.
        rv = self.app.delete('/v1.0/study/%i' % workflow.study_id, headers=self.logged_in_headers())
        self.assert_success(rv)


    def test_get_documentation_populated_in_end(self):
        workflow = self.create_workflow('random_fact')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        self.assertEqual("Task_User_Select_Type", task.name)
        self.assertEqual(3, len(task.form["fields"][0]["options"]))
        self.assertIsNotNone(task.documentation)
        self.complete_form(workflow, workflow_api.next_task, {"type": "norris"})
        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual("EndEvent_0u1cgrf", workflow_api.next_task.name)
        self.assertIsNotNone(workflow_api.next_task.documentation)
        self.assertTrue("norris" in workflow_api.next_task.documentation)

    def test_load_workflow_from_outdated_spec(self):
        # Start the basic two_forms workflow and complete a task.
        workflow = self.create_workflow('two_forms')
        workflow_api_1 = self.get_workflow_api(workflow)
        self.complete_form(workflow, workflow_api_1.next_task, {"color": "blue"})

        # Modify the specification, with a major change that alters the flow and can't be deserialized
        # effectively, if it uses the latest spec files.
        file_path = os.path.join(app.root_path, '..', 'tests', 'data', 'two_forms', 'modified', 'two_forms_struc_mod.bpmn')
        spec = self.workflow_spec_service.get_spec('two_forms')
        self.replace_file(spec, "two_forms.bpmn", file_path)

        # This should use the original workflow spec, and just move to the next task
        workflow_api_2 = self.get_workflow_api(workflow)
        self.assertEqual('StepTwo', workflow_api_2.next_task.name)

        workflow_api_3 = self.restart_workflow_api(workflow_api_2, clear_data=True)
        # This should restart the workflow and we should be back on StepOne
        self.assertEqual('StepOne', workflow_api_3.next_task.name)

        # Assure this hard_reset sticks (added this after a bug was found)
        # Again, we should be on StepOne
        workflow_api_4 = self.get_workflow_api(workflow)
        self.assertEqual('StepOne', workflow_api_4.next_task.name)

    def test_reset_workflow_from_broken_spec(self):
        # Start the basic two_forms workflow and complete a task.
        workflow = self.create_workflow('two_forms')
        workflow_api = self.get_workflow_api(workflow)
        self.complete_form(workflow, workflow_api.next_task, {"color": "blue"})
        # self.assertTrue(workflow_api.is_latest_spec)

        # Break the bpmn json
        workflow.bpmn_workflow_json = '{"something":"broken"}'
        session.add(workflow)
        session.commit()

        # Try to load the workflow, we should get an error
        with self.assertRaises(Exception):
            workflow_api = self.complete_form(workflow, workflow_api.next_task, {"name": "Dan"})

        # Now, Reset the workflow, and we should not get an error
        workflow_api = self.restart_workflow_api(workflow_api, clear_data=True)
        self.assertIsNotNone(workflow_api)

    def test_manual_task_with_external_documentation(self):
        workflow = self.create_workflow('manual_task_with_external_documentation')

        # Complete the form in the workflow.
        task = self.get_workflow_api(workflow).next_task
        workflow_api = self.complete_form(workflow, task, {"name": "Dan"})

        workflow = self.get_workflow_api(workflow)
        self.assertEqual('Task_Manual_One', workflow.next_task.name)
        self.assertEqual('ManualTask', workflow_api.next_task.type)
        self.assertTrue('Markdown' in workflow_api.next_task.documentation)
        self.assertTrue('Dan' in workflow_api.next_task.documentation)

    def test_bpmn_extension_properties_are_populated(self):
        workflow = self.create_workflow('manual_task_with_external_documentation')

        # get the first form in the two form workflow.
        task = self.get_workflow_api(workflow).next_task
        self.assertEqual("JustAValue", task.properties['JustAKey'])



    def test_lookup_endpoint_for_task_field_enumerations(self):
        workflow = self.create_workflow('enum_options_with_search')
        # get the first form in the two form workflow.
        workflow = self.get_workflow_api(workflow)
        task = workflow.next_task
        field_id = task.form['fields'][0]['id']
        rv = self.app.get('/v1.0/workflow/%i/lookup/%s/%s?query=%s&limit=5' %
                          (workflow.id, task.name, field_id, 'c'), # All records with a word that starts with 'c'
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        results = json.loads(rv.get_data(as_text=True))
        self.assertEqual(5, len(results))
        self.assert_options_populated(results, ['CUSTOMER_NUMBER', 'CUSTOMER_NAME', 'CUSTOMER_CLASS_MEANING'])

    def test_lookup_endpoint_for_task_field_using_lookup_entry_id(self):
        workflow = self.create_workflow('enum_options_with_search')
        # get the first form in the two form workflow.
        workflow = self.get_workflow_api(workflow)
        task = workflow.next_task
        field_id = task.form['fields'][0]['id']
        rv = self.app.get('/v1.0/workflow/%i/lookup/%s/%s?query=%s&limit=5' %
                          (workflow.id, task.name, field_id, 'c'), # All records with a word that starts with 'c'
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        results = json.loads(rv.get_data(as_text=True))
        self.assertEqual(5, len(results))
        self.assert_options_populated(results, ['CUSTOMER_NUMBER', 'CUSTOMER_NAME', 'CUSTOMER_CLASS_MEANING'])

        # Use the lookup to find a specific record, rather than running a search.
        rv = self.app.get('/v1.0/workflow/%i/lookup/%s/%s?value=%s' %
                          (workflow.id, task.name, field_id, results[0]['CUSTOMER_NUMBER']),
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        results = json.loads(rv.get_data(as_text=True))
        self.assertEqual(1, len(results))
        self.assert_options_populated(results, ['CUSTOMER_NUMBER', 'CUSTOMER_NAME', 'CUSTOMER_CLASS_MEANING'])
        self.assertNotIn('id', results[0], "Don't include the internal id, that can be very confusing, and should not be used.")

    def test_lookup_endpoint_also_works_for_enum(self):
        # Naming here get's a little confusing.  fields can be marked as enum or autocomplete.
        # In the event of an auto-complete it's a type-ahead search field, for an enum the
        # the key/values from the spreadsheet are added directly to the form and it shows up as
        # a dropdown.  This tests the case of wanting to get additional data when a user selects
        # something from a dropdown.
        workflow = self.create_workflow('enum_options_from_file')
        # get the first form in the two form workflow.
        workflow = self.get_workflow_api(workflow)
        task = workflow.next_task
        field_id = task.form['fields'][0]['id']
        option_id = task.form['fields'][0]['options'][0]['id']
        rv = self.app.get('/v1.0/workflow/%i/lookup/%s/%s?value=%s' %
                          (workflow.id, task.name, field_id, option_id), # All records with a word that starts with 'c'
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        results = json.loads(rv.get_data(as_text=True))
        self.assertEqual(1, len(results))
        self.assert_options_populated(results, ['CUSTOMER_NUMBER', 'CUSTOMER_NAME', 'CUSTOMER_CLASS_MEANING'])
        self.assertIsInstance(results[0], dict)

    def test_enum_from_task_data(self):
        workflow = self.create_workflow('enum_options_from_task_data')
        # get the first form in the two form workflow.
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        workflow_api = self.complete_form(workflow, task, {'invitees': [
            {'first_name': 'Alistair', 'last_name': 'Aardvark', 'age': 43, 'likes_pie': True, 'num_lumps': 21, 'secret_id': 'Antimony', 'display_name': 'Professor Alistair A. Aardvark'},
            {'first_name': 'Berthilda', 'last_name': 'Binturong', 'age': 12, 'likes_pie': False, 'num_lumps': 34, 'secret_id': 'Beryllium', 'display_name': 'Dr. Berthilda B. Binturong'},
            {'first_name': 'Chesterfield', 'last_name': 'Capybara', 'age': 32, 'likes_pie': True, 'num_lumps': 1, 'secret_id': 'Cadmium', 'display_name': 'The Honorable C. C. Capybara'},
        ]})
        task = workflow_api.next_task

        field_id = task.form['fields'][0]['id']
        options = task.form['fields'][0]['options']
        self.assertEqual(3, len(options))
        option_id = options[0]['id']
        self.assertEqual('Professor Alistair A. Aardvark', options[0]['name'])
        self.assertEqual('Dr. Berthilda B. Binturong', options[1]['name'])
        self.assertEqual('The Honorable C. C. Capybara', options[2]['name'])
        self.assertEqual('Alistair', options[0]['data']['first_name'])
        self.assertEqual('Berthilda', options[1]['data']['first_name'])
        self.assertEqual('Chesterfield', options[2]['data']['first_name'])

    def test_lookup_endpoint_for_task_ldap_field_lookup(self):
        workflow = self.create_workflow('ldap_lookup')
        # get the first form
        workflow = self.get_workflow_api(workflow)
        task = workflow.next_task
        field_id = task.form['fields'][0]['id']
        # lb3dp is a user record in the mock ldap responses for tests.
        rv = self.app.get('/v1.0/workflow/%s/lookup/%s/%s?query=%s&limit=5' %
                          (workflow.id, task.name, field_id, 'lb3dp'),
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        results = json.loads(rv.get_data(as_text=True))
        self.assert_options_populated(results, ['telephone_number', 'affiliation', 'uid', 'title',
                                                'given_name', 'department', 'date_cached', 'sponsor_type',
                                                'display_name', 'email_address'])
        self.assertEqual(1, len(results))

    def test_sub_process(self):
        workflow = self.create_workflow('subprocess')

        workflow_api = self.get_workflow_api(workflow)
        navigation = workflow_api.navigation
        task = workflow_api.next_task

        self.assertEqual(5, len(navigation))
        self.assertEqual("UserTask", task.type)
        self.assertEqual("Activity_A", task.name)
        self.assertEqual("My Sub Process", task.process_name)
        workflow_api = self.complete_form(workflow, task, {"FieldA": "Dan"})
        task = workflow_api.next_task
        self.assertIsNotNone(task)

        self.assertEqual("Activity_B", task.name)
        self.assertEqual("Sub Workflow Example", task.process_name)
        workflow_api = self.complete_form(workflow, task, {"FieldB": "Dan"})
        self.assertEqual(WorkflowStatus.complete, workflow_api.status)

    def test_update_task_resets_token(self):
        workflow = self.create_workflow('exclusive_gateway')

        # Start the workflow.
        first_task = self.get_workflow_api(workflow).next_task
        self.complete_form(workflow, first_task, {"has_bananas": True})
        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual('Task_Num_Bananas', workflow_api.next_task.name)

        # Trying to re-submit the initial task, and answer differently, should result in an error.
        self.complete_form(workflow, first_task, {"has_bananas": False}, error_code="invalid_state")

        # Go ahead and set the number of bananas.
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        self.complete_form(workflow, task, {"num_bananas": 4})
        # We are now at the end of the workflow.

        # Make the old task the current task.
        rv = self.app.put('/v1.0/workflow/%i/task/%s/set_token' % (workflow.id, first_task.id),
                          headers=self.logged_in_headers(),
                          content_type="application/json")
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        workflow_api = WorkflowApiSchema().load(json_data)

        # Assure the Next Task is the one we just reset the token to be on.
        self.assertEqual("Task_Has_Bananas", workflow_api.next_task.name)

        # Go ahead and get that workflow one more time, it should still be right.
        workflow_api = self.get_workflow_api(workflow)

        # Assure the Next Task is the one we just reset the token to be on.
        self.assertEqual("Task_Has_Bananas", workflow_api.next_task.name)

        # The next task should be a different value.
        self.complete_form(workflow, workflow_api.next_task, {"has_bananas": False})
        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual('Task_Why_No_Bananas', workflow_api.next_task.name)

    def test_update_task_when_locked(self):
        workflow = self.create_workflow('simple_form')
        workflow_model = session.query(WorkflowModel).filter(WorkflowModel.id == workflow.id).first()
        self.assertEqual(None, workflow.state)
        self.assertEqual(None, workflow_model.state)

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        form_data = {'yes': True,
                     'no': True}
        # Make sure we can run the workflow when it is *not* locked
        self.complete_form(workflow, task, form_data)

        # Do it again, but lock the workflow
        workflow = self.create_workflow('simple_form')
        workflow_api = self.get_workflow_api(workflow)

        workflow.state = 'locked'
        session.commit()

        self.assertEqual('locked', workflow.state)
        workflow_model = session.query(WorkflowModel).filter(WorkflowModel.id == workflow.id).first()
        self.assertEqual('locked', workflow_model.state)

        task = workflow_api.next_task

        # Make sure we get the `locked_workflow` error
        self.complete_form(workflow, task, form_data, error_code='locked_workflow')

        print('test_update_task_when_locked')
