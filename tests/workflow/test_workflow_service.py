import json
import unittest

from tests.base_test import BaseTest

from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService
from SpiffWorkflow import Task as SpiffTask, WorkflowException
from example_data import ExampleDataLoader
from crc import db
from crc.models.task_event import TaskEventModel
from crc.models.api_models import Task
from crc.models.file import FileModel
from crc.api.common import ApiError


class TestWorkflowService(BaseTest):

    def test_documentation_processing_handles_replacements(self):
        self.load_example_data()
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

        self.load_example_data()
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
        self.load_example_data()
        workflow = self.create_workflow('enum_options_from_file')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()
        WorkflowService.process_options(task, task.task_spec.form.fields[0])
        options = task.task_spec.form.fields[0].options
        self.assertEqual(29, len(options))
        self.assertEqual('0', options[0]['id'])
        self.assertEqual("Other", options[0]['name'])

    def test_random_data_populate_form_on_auto_complete(self):
        self.load_example_data()
        workflow = self.create_workflow('enum_options_with_search')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()
        task_api = WorkflowService.spiff_task_to_api_task(task, add_docs_and_forms=True)
        WorkflowService.populate_form_with_random_data(task, task_api, required_only=False)
        self.assertTrue(isinstance(task.data["sponsor"], dict))

    def test_dmn_evaluation_errors_in_oncomplete_raise_api_errors_during_validation(self):
        workflow_spec_model = self.load_test_spec("decision_table_invalid")
        with self.assertRaises(ApiError):
            WorkflowService.test_spec(workflow_spec_model.id)


    def test_expressions_in_forms(self):
        workflow_spec_model = self.load_test_spec("form_expressions")
        WorkflowService.test_spec(workflow_spec_model.id)

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

    def test_get_primary_workflow(self):

        workflow = self.create_workflow('hello_world')
        workflow_spec_id = workflow.workflow_spec.id
        primary_workflow = WorkflowService.get_primary_workflow(workflow_spec_id)
        self.assertIsInstance(primary_workflow, FileModel)
        self.assertEqual(workflow_spec_id, primary_workflow.workflow_spec_id)
        self.assertEqual('hello_world.bpmn', primary_workflow.name)
