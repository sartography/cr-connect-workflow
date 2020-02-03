import string
import random

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


    def test_workflow_with_parallel_forms(self):
        self.load_example_data()
        workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id="parallel_tasks").first()
        processor = WorkflowProcessor.create(workflow_spec_model.id)
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(4, len(next_user_tasks))
        self._complete_form_with_random_data(next_user_tasks[0])
        self._complete_form_with_random_data(next_user_tasks[1])
        self._complete_form_with_random_data(next_user_tasks[2])
        self._complete_form_with_random_data(next_user_tasks[3])
        processor.complete_task(next_user_tasks[0])
        processor.complete_task(next_user_tasks[1])
        processor.complete_task(next_user_tasks[2])
        processor.complete_task(next_user_tasks[3])
        # There are another 4 tasks to complete (each task, had a follow up task in the parallel list)
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(4, len(next_user_tasks))
        self._complete_form_with_random_data(next_user_tasks[0])
        self._complete_form_with_random_data(next_user_tasks[1])
        self._complete_form_with_random_data(next_user_tasks[2])
        self._complete_form_with_random_data(next_user_tasks[3])
        processor.complete_task(next_user_tasks[0])
        processor.complete_task(next_user_tasks[1])
        processor.complete_task(next_user_tasks[2])
        processor.complete_task(next_user_tasks[3])
        processor.do_engine_steps()
        self.assertTrue(processor.bpmn_workflow.is_completed())

    # def test_workflow_with_docx_template(self):
    #     self.load_example_data()
    #     files = session.query(FileModel).filter_by(workflow_spec_id='docx').all()
    #     self.assertEquals(2, len(files))
    #     workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id="docx").first()
    #     processor = WorkflowProcessor.create(workflow_spec_model.id)
    #     self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
    #     next_user_tasks = processor.next_user_tasks()
    #     self.assertEqual(1, len(next_user_tasks))
    #     task = next_user_tasks[0]
    #     self.assertEqual("task_gather_information", task.get_name())
    #     self._complete_form_with_random_data(task)
    #     processor.complete_task(task)
    #     processor.do_engine_steps()

        # workflow_files = session.query(FileModel).filter_by(workflow_id=).all()

    def _randomString(self, stringLength=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(stringLength))

    def _complete_form_with_random_data(self,task):
        form_data = {}
        for field in task.task_spec.form.fields:
            form_data[field.id] = self._randomString()
        if task.data is None:
            task.data = {}
        task.data.update(form_data)
