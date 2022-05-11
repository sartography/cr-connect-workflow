from tests.base_test import BaseTest

from crc import session
from flask_bpmn.api.api_error import ApiError
from crc.models.workflow import WorkflowModel
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService

from unittest.mock import patch

import json


class TestWorkflowService(BaseTest):

    def test_documentation_processing_handles_replacements(self):

        workflow = self.create_workflow('random_fact')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()

        task = processor.next_task()
        task.task_spec.documentation = "Some simple docs"
        docs = WorkflowService._process_documentation(task)
        self.assertEqual("Some simple docs", docs)

        task.data = {"replace_me": "new_thing"}
        task.task_spec.documentation = "{{replace_me}}"
        docs = WorkflowService._process_documentation(task)
        self.assertEqual("new_thing", docs)

        documentation = """
# Bigger Test

  * bullet one
  * bullet two has {{replace_me}}

# other stuff.
        """
        expected = """
# Bigger Test

  * bullet one
  * bullet two has new_thing

# other stuff.
        """
        task.task_spec.documentation = documentation
        result = WorkflowService._process_documentation(task)
        self.assertEqual(expected, result)

    def test_documentation_processing_handles_conditionals(self):


        workflow = self.create_workflow('random_fact')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()

        task = processor.next_task()
        task.task_spec.documentation = "This test {% if works == 'yes' %}works{% endif %}"
        docs = WorkflowService._process_documentation(task)
        self.assertEqual("This test ", docs)

        task.data = {"works": 'yes'}
        docs = WorkflowService._process_documentation(task)
        self.assertEqual("This test works", docs)

    def test_enum_options_from_file(self):

        workflow = self.create_workflow('enum_options_from_file')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()
        WorkflowService.process_options(task, task.task_spec.form.fields[0])
        options = task.task_spec.form.fields[0].options
        self.assertEqual(29, len(options))
        self.assertEqual('0', options[0].id)
        self.assertEqual("Other", options[0].name)

    def test_random_data_populate_form_on_auto_complete(self):

        workflow = self.create_workflow('enum_options_with_search')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()
        task_api = WorkflowService.spiff_task_to_api_task(task, add_docs_and_forms=True)
        WorkflowService.populate_form_with_random_data(task, task_api, required_only=False)
        self.assertTrue(isinstance(task.data["sponsor"], str))

    def test_dmn_evaluation_errors_in_oncomplete_raise_api_errors_during_validation(self):
        workflow_spec_model = self.load_test_spec("decision_table_invalid")
        with self.assertRaises(ApiError):
            WorkflowService.test_spec(workflow_spec_model.id)

    def test_expressions_in_forms(self):
        workflow_spec_model = self.load_test_spec("form_expressions")
        WorkflowService.test_spec(workflow_spec_model.id)

    def test_task_properties(self):
        workflow = self.create_workflow("form_extentsions")
        workflow_api = self.get_workflow_api(workflow)

        # Start with task 1
        first_task = workflow_api.next_task
        self.assertIn('clear_data', first_task.properties)
        self.complete_form(workflow, first_task, {'field1': 'some data'})
        workflow_api = self.get_workflow_api(workflow)

        # Move to task 2
        second_task = workflow_api.next_task
        self.assertIn('field1', workflow_api.next_task.data )
        result = self.complete_form(workflow, second_task, {})
        workflow_api = self.restart_workflow_api(result)

        # Move back to task 1
        first_task = workflow_api.next_task
        self.assertNotIn("field1", workflow_api.next_task.data)
        self.assertNotIn("field1", first_task.data)

    def test_set_value(self):
        destiation = {}
        path = "a.b.c"
        value = "abracadara"
        result = WorkflowService.set_dot_value(path, value, destiation)
        self.assertEqual(value, destiation["a"]["b"]["c"])

    def test_get_dot_value(self):
        path = "a.b.c"
        source = {"a":{"b":{"c" : "abracadara"}}, "a.b.c":"garbage"}
        result = WorkflowService.get_dot_value(path, source)
        self.assertEqual("abracadara", result)

        result2 = WorkflowService.get_dot_value(path, {"a.b.c":"garbage"})
        self.assertEqual("garbage", result2)

    @patch('crc.services.workflow_processor.WorkflowProcessor')
    def test_test_spec_cleans_up_after_unknown_exception(self, mock_processor):
        """We have a finally clause in test_spec that cleans up test data for the validation.
        Make sure the cleanup clause is called when we have an unknown exception"""
        mock_processor.side_effect = Exception('Mocked error message')
        mock_processor.return_value = 'Mocked error message'
        spec_model = self.load_test_spec('hello_world')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual('unknown_exception', json_data[0]['code'])
        workflows = session.query(WorkflowModel).all()
        self.assertEqual(0, len(workflows))
