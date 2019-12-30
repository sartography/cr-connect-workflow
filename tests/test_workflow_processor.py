import unittest

from crc import db
from crc.models import WorkflowSpecModel, WorkflowStatus
from crc.workflow_processor import WorkflowProcessor
from tests.base_test import BaseTest


class TestWorkflowProcessor(BaseTest, unittest.TestCase):

    def test_create_and_complete_workflow(self):
        self.load_example_data()
        workflow_spec_model = db.session.query(WorkflowSpecModel).filter_by(id="random_fact").first()

        processor = WorkflowProcessor.create(workflow_spec_model.id)

        self.assertIsNotNone(processor)
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(1, len(next_user_tasks))
        task = next_user_tasks[0]
        self.assertEqual("Task_User_Select_Type", task.get_name())
        model = {"Fact.type": "buzzword"}
        if task.data is None:
            task.data = {}
        task.data.update(model)
        processor.complete_task(task)
        self.assertEqual(WorkflowStatus.waiting, processor.get_status())
        processor.do_engine_steps()
        self.assertEqual(WorkflowStatus.complete, processor.get_status())
        data = processor.get_data()
        self.assertIsNotNone(data)
        self.assertIn("details", data)
