import json

from tests.base_test import BaseTest

from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService
from SpiffWorkflow import Task as SpiffTask, WorkflowException
from example_data import ExampleDataLoader
from crc import db
from crc.models.stats import TaskEventModel
from crc.models.api_models import Task
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
        self.assertEqual(28, len(options))
        self.assertEqual('1000', options[0]['id'])
        self.assertEqual("UVA - INTERNAL - GM USE ONLY", options[0]['name'])

    def test_random_data_populate_form_on_auto_complete(self):
        self.load_example_data()
        workflow = self.create_workflow('enum_options_with_search')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()
        task_api = WorkflowService.spiff_task_to_api_task(task, add_docs_and_forms=True)
        WorkflowService.populate_form_with_random_data(task, task_api, required_only=False)
        self.assertTrue(isinstance(task.data["sponsor"], dict))

    def test_fix_legacy_data_model_for_rrt(self):
        ExampleDataLoader().load_rrt() # Make sure the research_rampup is loaded, as it's not a test spec.
        workflow = self.create_workflow('research_rampup')
        processor = WorkflowProcessor(workflow, validate_only=True)

        # Use the test spec code to complete the workflow of research rampup.
        while not processor.bpmn_workflow.is_completed():
            processor.bpmn_workflow.do_engine_steps()
            tasks = processor.bpmn_workflow.get_tasks(SpiffTask.READY)
            for task in tasks:
                task_api = WorkflowService.spiff_task_to_api_task(task, add_docs_and_forms=True)
                WorkflowService.populate_form_with_random_data(task, task_api, False)
                task.complete()
                # create the task events
                WorkflowService.log_task_action('dhf8r', workflow, task,
                                                WorkflowService.TASK_ACTION_COMPLETE,
                                                version=processor.get_version_string())
        processor.save()
        db.session.commit()

        WorkflowService.fix_legacy_data_model_for_rrt()

        # All tasks should now have data associated with them.
        task_logs = db.session.query(TaskEventModel) \
            .filter(TaskEventModel.workflow_id == workflow.id) \
            .filter(TaskEventModel.action == WorkflowService.TASK_ACTION_COMPLETE) \
            .order_by(TaskEventModel.date).all()  # Get them back in order.

        self.assertEqual(17, len(task_logs))
        for log in task_logs:
            task = processor.bpmn_workflow.get_tasks_from_spec_name(log.task_name)[0]
            self.assertIsNotNone(log.form_data)
            # Each task should have the data in the form for that task in the task event.
            if hasattr(task.task_spec, 'form'):
                for field in task.task_spec.form.fields:
                    if field.has_property(Task.PROP_OPTIONS_REPEAT):
                        self.assertIn(field.get_property(Task.PROP_OPTIONS_REPEAT), log.form_data)
                    else:
                        self.assertIn(field.id, log.form_data)

        # Some spot checks:
        # The first task should be empty, with all the data removed.
        self.assertEqual({}, task_logs[0].form_data)


    def test_dmn_evaluation_errors_in_oncomplete_raise_api_errors_during_validation(self):
        workflow_spec_model = self.load_test_spec("decision_table_invalid")
        with self.assertRaises(ApiError):
            WorkflowService.test_spec(workflow_spec_model.id)