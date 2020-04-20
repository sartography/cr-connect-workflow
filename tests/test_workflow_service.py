import json
import os

from crc import session, app
from crc.models.api_models import WorkflowApiSchema, Task
from crc.models.file import FileModelSchema
from crc.models.stats import WorkflowStatsModel, TaskEventModel
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowSpecModelSchema, WorkflowModel, WorkflowStatus
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService
from tests.base_test import BaseTest


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
        WorkflowService._process_options(task, task.task_spec.form.fields[0])
        options = task.task_spec.form.fields[0].options
        self.assertEquals(19, len(options))
        self.assertEquals(1000, options[0]['id'])
        self.assertEquals("UVA - INTERNAL - GM USE ONLY", options[0]['name'])