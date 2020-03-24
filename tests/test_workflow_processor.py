import os
import string
import random
from unittest.mock import patch

from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent

from crc import session, db, app
from crc.api.common import ApiError
from crc.models.file import FileModel, FileDataModel, CONTENT_TYPES
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowSpecModel, WorkflowStatus, WorkflowModel
from crc.services.file_service import FileService
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
        workflow_spec_model = self.load_test_spec("random_fact")
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
        workflow_spec_model = self.load_test_spec("decision_table")
        files = session.query(FileModel).filter_by(workflow_spec_id='decision_table').all()
        self.assertEqual(2, len(files))
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
        workflow_spec_model = self.load_test_spec("parallel_tasks")
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
        workflow_spec_model = self.load_test_spec("parallel_tasks")
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
        workflow_spec_model = self.load_test_spec("random_fact")
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

    def test_workflow_validation_error_is_properly_raised(self):
        self.load_example_data()
        workflow_spec_model = self.load_test_spec("invalid_spec")
        study = session.query(StudyModel).first()
        with self.assertRaises(ApiError) as context:
            WorkflowProcessor.create(study.id, workflow_spec_model.id)
        self.assertEqual("workflow_validation_error", context.exception.code)
        self.assertTrue("bpmn:startEvent" in context.exception.message)

    def test_workflow_spec_key_error(self):
        """Frequently seeing errors in the logs about a 'Key' error, where a workflow
        references something that doesn't exist in the midst of processing. Want to
        make sure we produce errors to the front end that allows us to debug this."""
        # Start the two_forms workflow, and enter some data in the first form.
        self.load_example_data()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("two_forms")
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        workflow_model = db.session.query(WorkflowModel).filter(WorkflowModel.study_id == study.id).first()
        self.assertEqual(workflow_model.workflow_spec_id, workflow_spec_model.id)
        task = processor.next_task()
        task.data = {"color": "blue"}
        processor.complete_task(task)

        # Modify the specification, with a major change.
        file_path = os.path.join(app.root_path, '..', 'tests', 'data', 'two_forms', 'mods', 'two_forms_struc_mod.bpmn')
        self.replace_file("two_forms.bpmn", file_path)

        # Attemping a soft update on a structural change should raise a sensible error.
        with self.assertRaises(ApiError) as context:
            processor3 = WorkflowProcessor(workflow_model, soft_reset=True)
        self.assertEqual("unexpected_workflow_structure", context.exception.code)




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

    def test_load_study_information(self):
        """ Test a workflow that includes requests to pull in Study Details."""

        self.load_example_data()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("study_details")
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        processor.do_engine_steps()
        task = processor.bpmn_workflow.last_task
        self.assertIsNotNone(task.data)
        self.assertIn("study", task.data)
        self.assertIn("info", task.data["study"])
        self.assertIn("title", task.data["study"]["info"])
        self.assertIn("last_updated", task.data["study"]["info"])
        self.assertIn("sponsor", task.data["study"]["info"])

    def test_spec_versioning(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("decision_table")
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        self.assertTrue(processor.get_spec_version().startswith('v1.1'))
        file_service = FileService()

        file_service.add_workflow_spec_file(workflow_spec_model, "new_file.txt", "txt", b'blahblah')
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        self.assertTrue(processor.get_spec_version().startswith('v1.1.1'))

        file_path = os.path.join(app.root_path, '..', 'tests', 'data', 'docx', 'docx.bpmn')
        file = open(file_path, "rb")
        data = file.read()

        file_model = db.session.query(FileModel).filter(FileModel.name == "decision_table.bpmn").first()
        file_service.update_file(file_model, data, "txt")
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        self.assertTrue(processor.get_spec_version().startswith('v2.1.1'))

    def test_restart_workflow(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("two_forms")
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        workflow_model = db.session.query(WorkflowModel).filter(WorkflowModel.study_id == study.id).first()
        self.assertEqual(workflow_model.workflow_spec_id, workflow_spec_model.id)
        task = processor.next_task()
        task.data = {"key": "Value"}
        processor.complete_task(task)
        task_before_restart = processor.next_task()
        processor.hard_reset()
        task_after_restart = processor.next_task()

        self.assertNotEqual(task.get_name(), task_before_restart.get_name())
        self.assertEqual(task.get_name(), task_after_restart.get_name())
        self.assertEqual(task.data, task_after_restart.data)

    def test_soft_reset(self):
        self.load_example_data()

        # Start the two_forms workflow, and enter some data in the first form.
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("two_forms")
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        workflow_model = db.session.query(WorkflowModel).filter(WorkflowModel.study_id == study.id).first()
        self.assertEqual(workflow_model.workflow_spec_id, workflow_spec_model.id)
        task = processor.next_task()
        task.data = {"color": "blue"}
        processor.complete_task(task)

        # Modify the specification, with a minor text change.
        file_path = os.path.join(app.root_path, '..', 'tests', 'data', 'two_forms', 'mods', 'two_forms_text_mod.bpmn')
        self.replace_file("two_forms.bpmn", file_path)

        # Setting up another processor should not error out, but doesn't pick up the update.
        workflow_model.bpmn_workflow_json = processor.serialize()
        processor2 = WorkflowProcessor(workflow_model)
        self.assertEqual("Step 1", processor2.bpmn_workflow.last_task.task_spec.description)
        self.assertNotEqual("# This is some documentation I wanted to add.",
                          processor2.bpmn_workflow.last_task.task_spec.documentation)

        # You can do a soft update and get the right response.
        processor3 = WorkflowProcessor(workflow_model, soft_reset=True)
        self.assertEqual("Step 1", processor3.bpmn_workflow.last_task.task_spec.description)
        self.assertEqual("# This is some documentation I wanted to add.",
                          processor3.bpmn_workflow.last_task.task_spec.documentation)



    def test_hard_reset(self):
        self.load_example_data()

        # Start the two_forms workflow, and enter some data in the first form.
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("two_forms")
        processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
        workflow_model = db.session.query(WorkflowModel).filter(WorkflowModel.study_id == study.id).first()
        self.assertEqual(workflow_model.workflow_spec_id, workflow_spec_model.id)
        task = processor.next_task()
        task.data = {"color": "blue"}
        processor.complete_task(task)
        next_task = processor.next_task()
        self.assertEqual("Step 2", next_task.task_spec.description)

        # Modify the specification, with a major change that alters the flow and can't be serialized effectively.
        file_path = os.path.join(app.root_path, '..', 'tests', 'data', 'two_forms', 'mods', 'two_forms_struc_mod.bpmn')
        self.replace_file("two_forms.bpmn", file_path)

        # Assure that creating a new processor doesn't cause any issues, and maintains the spec version.
        workflow_model.bpmn_workflow_json = processor.serialize()
        processor2 = WorkflowProcessor(workflow_model)
        self.assertTrue(processor2.get_spec_version().startswith("v1 ")) # Still at version 1.

        # Do a hard reset, which should bring us back to the beginning, but retain the data.
        processor3 = WorkflowProcessor(workflow_model, hard_reset=True)
        self.assertEqual("Step 1", processor3.next_task().task_spec.description)
        self.assertEqual({"color": "blue"}, processor3.next_task().data)
        processor3.complete_task(processor3.next_task())
        self.assertEqual("New Step", processor3.next_task().task_spec.description)
        self.assertEqual("blue", processor3.next_task().data["color"])

    def test_get_latest_spec_version(self):
        workflow_spec_model = self.load_test_spec("two_forms")
        version = WorkflowProcessor.get_latest_version_string("two_forms")
        self.assertTrue(version.startswith("v1 "))

    def test_status_bpmn(self):
        self.load_example_data()

        specs = session.query(WorkflowSpecModel).all()

        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("status")

        for enabled in [True, False]:
            processor = WorkflowProcessor.create(study.id, workflow_spec_model.id)
            task = processor.next_task()

            # Turn all specs on or off
            task.data = {"some_input": enabled}
            processor.complete_task(task)

            # Finish out rest of workflow
            while processor.get_status() == WorkflowStatus.waiting:
                task = processor.next_task()
                processor.complete_task(task)

            self.assertEqual(processor.get_status(), WorkflowStatus.complete)

            # Enabled status of all specs should match the value set in the first task
            for spec in specs:
                self.assertEqual(task.data[spec.id], enabled)
