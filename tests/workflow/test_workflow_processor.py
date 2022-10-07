import json
import os

from SpiffWorkflow.task import TaskState
from SpiffWorkflow.bpmn.serializer.BpmnSerializer import BpmnSerializer

from tests.base_test import BaseTest

from SpiffWorkflow.bpmn.specs.events import EndEvent
from SpiffWorkflow.camunda.specs.UserTask import FormField
from flask import g

from crc import session, db, app
from crc.api.common import ApiError
from crc.models.file import FileModel
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowStatus
from crc.models.user import UserModel
from crc.services.spec_file_service import SpecFileService
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService


class TestWorkflowProcessor(BaseTest):

    @staticmethod
    def _populate_form_with_random_data(task):
        api_task = WorkflowService.spiff_task_to_api_task(task, add_docs_and_forms=True)
        WorkflowService.populate_form_with_random_data(task, api_task, required_only=False)

    @staticmethod
    def get_processor(study_model, spec_model):
        workflow_model = StudyService._create_workflow_model(study_model, spec_model)
        return WorkflowProcessor(workflow_model)

    def test_create_and_complete_workflow(self):
        self.add_studies()
        workflow_spec_model = self.load_test_spec("random_fact")
        study = session.query(StudyModel).first()
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
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
        self.assertIn("FactService", data)

    def test_workflow_with_dmn(self):

        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("decision_table")
        files = SpecFileService.get_files(workflow_spec_model)
        self.assertEqual(2, len(files))
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
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
        self.create_reference_document()
        workflow_spec_model = self.load_test_spec("parallel_tasks")
        study = session.query(StudyModel).first()
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
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

        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("parallel_tasks")
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
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

        workflow_spec_model = self.load_test_spec("random_fact")
        study = session.query(StudyModel).first()
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
        task = processor.next_task()
        task.data = {"type": "buzzword"}
        processor.complete_task(task)
        self.assertEqual(WorkflowStatus.waiting, processor.get_status())
        processor.do_engine_steps()
        self.assertEqual(WorkflowStatus.complete, processor.get_status())
        task = processor.next_task()
        self.assertIsNotNone(task)
        self.assertIn("FactService", task.data)
        self.assertIsInstance(task.task_spec, EndEvent)

    def test_workflow_processor_returns_waiting_task_if_no_ready_tasks_exist(self):

        workflow_spec_model = self.load_test_spec("timer_inline")
        study = session.query(StudyModel).first()
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
        task = processor.next_task()
        task.data = {"type": "buzzword"}
        processor.complete_task(task)
        processor.do_engine_steps()
        task = processor.next_task()
        self.assertIsNotNone(task)
        self.assertEqual(task.state, TaskState.WAITING)

    def test_workflow_validation_error_is_properly_raised(self):

        workflow_spec_model = self.load_test_spec("invalid_spec")
        study = session.query(StudyModel).first()
        with self.assertRaises(ApiError) as context:
            self.get_processor(study, workflow_spec_model)
        self.assertEqual("workflow_validation_error", context.exception.code)
        self.assertTrue("bpmn:startEvent" in context.exception.message)


    def test_workflow_with_bad_expression_raises_sensible_error(self):


        workflow_spec_model = self.load_test_spec("invalid_expression")
        study = session.query(StudyModel).first()
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(1, len(next_user_tasks))
        self._populate_form_with_random_data(next_user_tasks[0])
        processor.complete_task(next_user_tasks[0])
        with self.assertRaises(ApiError) as context:
            processor.do_engine_steps()
        self.assertEqual("task_error", context.exception.code)

    def test_workflow_with_docx_template(self):
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("docx")
        files = SpecFileService.get_files(workflow_spec_model)
        self.assertEqual(2, len(files))
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
        self.assertEqual(WorkflowStatus.user_input_required, processor.get_status())
        next_user_tasks = processor.next_user_tasks()
        self.assertEqual(1, len(next_user_tasks))
        task = next_user_tasks[0]
        self.assertEqual("task_gather_information", task.get_name())
        self._populate_form_with_random_data(task)
        processor.complete_task(task)

        files = session.query(FileModel).filter_by(workflow_id=processor.get_workflow_id()).all()
        self.assertEqual(0, len(files))
        processor.do_engine_steps()
        files = session.query(FileModel).filter_by(workflow_id=processor.get_workflow_id()).all()
        self.assertEqual(1, len(files), "The task should create a new file.")
        self.assertIsNotNone(files[0].data)
        self.assertTrue(len(files[0].data) > 0)
        # Not going any farther here, assuming this is tested in libraries correctly.

    def test_load_study_information(self):
        """ Test a workflow that includes requests to pull in Study Details."""

        self.add_studies()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("study_details")
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
        task = processor.bpmn_workflow.last_task
        self.assertIsNotNone(task.data)
        self.assertIn("StudyInfo", task.data)
        self.assertIn("info", task.data["StudyInfo"])
        self.assertIn("title", task.data["StudyInfo"]["info"])
        self.assertIn("last_updated", task.data["StudyInfo"]["info"])
        self.assertIn("sponsor", task.data["StudyInfo"]["info"])

    def test_hard_reset(self):

        # Start the two_forms workflow, and enter some data in the first form.
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("two_forms")
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
        self.assertEqual(processor.workflow_model.workflow_spec_id, workflow_spec_model.id)
        task = processor.next_task()
        task.data = {"color": "blue"}
        processor.complete_task(task)
        next_task = processor.next_task()
        self.assertEqual("Step 2", next_task.task_spec.description)

        # Modify the specification, with a major change that alters the flow and can't be serialized effectively.
        file_path = os.path.join(app.root_path, '..', 'tests', 'data', 'two_forms', 'modified', 'two_forms_struc_mod.bpmn')
        self.replace_file(workflow_spec_model, "two_forms.bpmn", file_path)

        # Assure that creating a new processor doesn't cause any issues, and maintains the spec version.
        processor.workflow_model.bpmn_workflow_json = processor.serialize()
        db.session.add(processor.workflow_model)  ## Assure this isn't transient, which was causing some errors.
        self.assertIsNotNone(processor.workflow_model.bpmn_workflow_json)
        processor2 = WorkflowProcessor(processor.workflow_model)
        # self.assertFalse(processor2.is_latest_spec) # Still at version 1.

        # Do a hard reset, which should bring us back to the beginning, but retain the data.
        WorkflowProcessor.reset(processor2.workflow_model)
        processor2 = WorkflowProcessor(processor2.workflow_model)
        processor3 = WorkflowProcessor(processor.workflow_model)
        processor3.do_engine_steps()
        self.assertEqual("Step 1", processor3.next_task().task_spec.description)
        # self.assertTrue(processor3.is_latest_spec) # Now at version 2.
        task = processor3.next_task()
        task.data = {"color": "blue"}
        processor3.complete_task(task)
        self.assertEqual("New Step", processor3.next_task().task_spec.description)
        self.assertEqual("blue", processor3.next_task().data["color"])

    def test_next_task_when_completing_sequential_steps_within_parallel(self):

        # Start the two_forms workflow, and enter some data in the first form.
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("nav_order")
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
        self.assertEqual(processor.workflow_model.workflow_spec_id, workflow_spec_model.id)
        ready_tasks = processor.get_ready_user_tasks()
        task = ready_tasks[2]
        self.assertEqual("B1", task.task_spec.name)
        processor.complete_task(task)
        processor.do_engine_steps()
        task = processor.next_task()
        self.assertEqual("B1_0", task.task_spec.name)
        processor.complete_task(task)
        processor.do_engine_steps()
        task = processor.next_task()
        self.assertEqual("B2", task.task_spec.name)
        processor.complete_task(task)
        processor.do_engine_steps()
        task = processor.next_task()
        self.assertEqual("B3", task.task_spec.name)
        processor.complete_task(task)
        processor.do_engine_steps()
        task = processor.next_task()
        self.assertEqual("B4", task.task_spec.name)
        processor.complete_task(task)
        processor.do_engine_steps()
        task = processor.next_task()
        self.assertEqual("A1", task.task_spec.name)

    def test_enum_with_no_choices_raises_api_error(self):

        workflow_spec_model = self.load_test_spec("random_fact")
        study = session.query(StudyModel).first()
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
        tasks = processor.next_user_tasks()
        task = tasks[0]
        field = FormField()
        field.id = "test_enum_field"
        field.type = "enum"
        field.options = []
        task.task_spec.form.fields.append(field)

        with self.assertRaises(ApiError):
            self._populate_form_with_random_data(task)


    def test_get_role_by_name(self):

        workflow_spec_model = self.load_test_spec("roles")
        study = session.query(StudyModel).first()
        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
        tasks = processor.next_user_tasks()
        task = tasks[0]
        self._populate_form_with_random_data(task)
        processor.complete_task(task)
        supervisor_task = processor.next_user_tasks()[0]
        self.assertEqual("supervisor", supervisor_task.task_spec.lane)

    def test_ability_to_deserialize_old_workflows(self):
        workflow_model = self.create_workflow("random_fact")
        processor = WorkflowProcessor(workflow_model)
        processor.do_engine_steps()  # Get the thing up and running.

        # Serlialize the workflow normally, but alter the version number, so we can exercise that older code
        old_school_json = json.loads(processor.serialize())
        old_school_json['serializer_version'] = "1.0-CRC"
        workflow_model.bpmn_workflow_json = json.dumps(old_school_json)
        db.session.add(workflow_model)
        db.session.commit()

        self.assertIsNone(processor._serializer.get_version(processor.bpmn_workflow))

        # assure there is no error when loading the workflpw up with the old style json.
        processor = WorkflowProcessor(workflow_model)
        new_json = processor.serialize()

        self.assertEqual(processor.SERIALIZER_VERSION, processor._serializer.get_version(new_json))
