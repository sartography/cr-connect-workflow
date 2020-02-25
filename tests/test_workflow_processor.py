import string
import random

from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent

from crc import session
from crc.api.common import ApiError
from crc.models.file import FileModel, FileDataModel
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowSpecModel, WorkflowStatus
from tests.base_test import BaseTest
from crc.services.workflow_processor import WorkflowProcessor


class TestWorkflowProcessor(BaseTest):

    def _randomString(self, stringLength=10):
        """Generate a random string of fixed length """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(stringLength))

    def _populate_form_with_random_data(self, task):
        form_data = {}
        for field in task.task_spec.form.fields:
            form_data[field.id] = self._randomString()
        if task.data is None:
            task.data = {}
        task.data.update(form_data)

    def test_create_and_complete_workflow(self):
        self.load_example_data()
        workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id="random_fact").first()
        study = session.query(StudyModel).first()
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        self.assertEqual(study.id, processor.bpmn_workflow.data[WorkflowProcessor.STUDY_ID_KEY])
        self.assertIsNotNone(processor)
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(1, len(next_user_tasks))
        task = next_user_tasks[0]
        self.assertEqual("Task_User_Select_Type", task.get_name())
        model = {"type": "buzzword"}
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
        study = session.query(StudyModel).first()
        files = session.query(FileModel).filter_by(workflow_spec_id='decision_table').all()
        self.assertEqual(2, len(files))
        workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id="decision_table").first()
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
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
        self.assertEqual("End", processor.bpmn_workflow.last_task.task_spec.name)
        self.assertEqual("Oh, Ginger.", processor.bpmn_workflow.last_task.data.get('message'))


    def test_workflow_with_parallel_forms(self):
        self.load_example_data()
        workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id="parallel_tasks").first()
        study = session.query(StudyModel).first()
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())

        # Complete the first steps of the 4 parallel tasks
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(4, len(next_user_tasks))
        self._populate_form_with_random_data(next_user_tasks[0])
        self._populate_form_with_random_data(next_user_tasks[1])
        self._populate_form_with_random_data(next_user_tasks[2])
        self._populate_form_with_random_data(next_user_tasks[3])
        processor.complete_task(next_user_tasks[0])
        processor.complete_task(next_user_tasks[1])
        processor.complete_task(next_user_tasks[2])
        processor.complete_task(next_user_tasks[3])

        # There are another 4 tasks to complete (each parallel task has a follow-up task)
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(4, len(next_user_tasks))
        self._populate_form_with_random_data(next_user_tasks[0])
        self._populate_form_with_random_data(next_user_tasks[1])
        self._populate_form_with_random_data(next_user_tasks[2])
        self._populate_form_with_random_data(next_user_tasks[3])
        processor.complete_task(next_user_tasks[0])
        processor.complete_task(next_user_tasks[1])
        processor.complete_task(next_user_tasks[2])
        processor.complete_task(next_user_tasks[3])
        processor.do_engine_steps()

        # Should be one last step after the above are complete
        final_user_tasks = processor.next_user_tasks()
        self.assertEqual(1, len(final_user_tasks))
        self._populate_form_with_random_data(final_user_tasks[0])
        processor.complete_task(final_user_tasks[0])

        processor.do_engine_steps()
        self.assertTrue(processor.bpmn_workflow.is_completed())

    def test_workflow_processor_knows_the_text_task_even_when_parallel(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id="parallel_tasks").first()
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(4, len(next_user_tasks))
        self.assertEqual(next_user_tasks[0], processor.next_task(), "First task in list of 4")

        # Complete the third open task, so do things out of order
        # this should cause the system to recommend the first ready task that is a
        # child of the last completed task.
        task = next_user_tasks[2]
        self._populate_form_with_random_data(task)
        processor.complete_task(task)
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(processor.bpmn_workflow.last_task, task)
        self.assertEqual(4, len(next_user_tasks))
        self.assertEqual(task.children[0], processor.next_task())

    def test_workflow_processor_returns_next_task_as_end_task_if_complete(self):
        self.load_example_data()
        workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id="random_fact").first()
        study = session.query(StudyModel).first()
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        processor.do_engine_steps()
        task = processor.next_task()
        task.data = {"type": "buzzword"}
        processor.complete_task(task)
        self.assertEqual(WorkflowStatus.waiting, processor.get_status())
        processor.do_engine_steps()
        self.assertEqual(WorkflowStatus.complete, processor.get_status())
        task = processor.next_task()
        self.assertIsNotNone(task)
        self.assertIn("details", task.data)
        self.assertIsInstance(task.task_spec, EndEvent)

    def test_workflow_with_bad_expression_raises_sensible_error(self):
        self.load_example_data()

        workflow_spec_model = self.load_test_spec("invalid_expression")
        study = session.query(StudyModel).first()
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        processor.do_engine_steps()
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(1, len(next_user_tasks))
        self._populate_form_with_random_data(next_user_tasks[0])
        processor.complete_task(next_user_tasks[0])
        with self.assertRaises(ApiError) as context:
            processor.do_engine_steps()
        self.assertEqual("invalid_expression", context.exception.code)

    def test_workflow_with_docx_template(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("docx")
        files = session.query(FileModel).filter_by(workflow_spec_id='docx').all()
        self.assertEqual(2, len(files))
        workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id="docx").first()
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(1, len(next_user_tasks))
        task = next_user_tasks[0]
        self.assertEqual("task_gather_information", task.get_name())
        self._populate_form_with_random_data(task)
        processor.complete_task(task)

        files = session.query(FileModel).filter_by(study_id=study.id, workflow_id=processor.get_workflow_id()).all()
        self.assertEqual(0, len(files))
        processor.do_engine_steps()
        files = session.query(FileModel).filter_by(study_id=study.id, workflow_id=processor.get_workflow_id()).all()
        self.assertEqual(1, len(files), "The task should create a new file.")
        file_data = session.query(FileDataModel).filter(FileDataModel.file_model_id == files[0].id).first()
        self.assertIsNotNone(file_data.data)
        self.assertTrue(len(file_data.data) > 0)
        # Not going any farther here, assuming this is tested in libraries correctly.
