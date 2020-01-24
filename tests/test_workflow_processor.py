from crc import session
from crc.models.file import FileModel
from crc.models.workflow import WorkflowSpecModel, WorkflowStatus
from tests.base_test import BaseTest
from crc.workflow_processor import WorkflowProcessor


class TestWorkflowProcessor(BaseTest):

    def test_create_and_complete_workflow(self):
        self.load_example_data()
        workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id="random_fact").first()

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

    def test_workflow_with_dmn(self):
        self.load_example_data()
        files = session.query(FileModel).filter_by(workflow_spec_id='decision_table').all()
        self.assertEquals(2, len(files))
        workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id="decision_table").first()
        processor = WorkflowProcessor.create(workflow_spec_model.id)
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(1, len(next_user_tasks))
        task = next_user_tasks[0]
        self.assertEqual("get_num_presents", task.get_name())
        model = {"num_presents": 1}
        if task.data is None:
            task.data = {}
        task.data.update(model)
        processor.complete_task(task)
        processor.do_engine_steps()
        data = processor.get_data()
        self.assertIsNotNone(data)
        self.assertIn("message", data)
        self.assertEqual("Oh, Ginger.", data.get('message'))
