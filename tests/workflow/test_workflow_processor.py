import json
import logging
import os
from unittest.mock import patch

from tests.base_test import BaseTest

from SpiffWorkflow.bpmn.specs.EndEvent import EndEvent
from SpiffWorkflow.camunda.specs.UserTask import FormField

from crc import session, db, app
from crc.api.common import ApiError
from crc.models.file import FileModel, FileDataModel
from crc.models.protocol_builder import ProtocolBuilderStudySchema
from crc.services.protocol_builder import ProtocolBuilderService
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowSpecModel, WorkflowStatus
from crc.services.file_service import FileService
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService


class TestWorkflowProcessor(BaseTest):

    def _populate_form_with_random_data(self, task):
        api_task = WorkflowService.spiff_task_to_api_task(task, add_docs_and_forms=True)
        WorkflowService.populate_form_with_random_data(task, api_task, required_only=False)

    def get_processor(self, study_model, spec_model):
        workflow_model = StudyService._create_workflow_model(study_model, spec_model)
        return WorkflowProcessor(workflow_model)

    def test_create_and_complete_workflow(self):
        self.load_example_data()
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
        self.load_example_data()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("decision_table")
        files = session.query(FileModel).filter_by(workflow_spec_id='decision_table').all()
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
        self.load_example_data()
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
        self.load_example_data()
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
        self.load_example_data()
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

    def test_workflow_validation_error_is_properly_raised(self):
        self.load_example_data()
        workflow_spec_model = self.load_test_spec("invalid_spec")
        study = session.query(StudyModel).first()
        with self.assertRaises(ApiError) as context:
            self.get_processor(study, workflow_spec_model)
        self.assertEqual("workflow_validation_error", context.exception.code)
        self.assertTrue("bpmn:startEvent" in context.exception.message)


    def test_workflow_with_bad_expression_raises_sensible_error(self):
        self.load_example_data()

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
        self.load_example_data()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("docx")
        files = session.query(FileModel).filter_by(workflow_spec_id='docx').all()
        self.assertEqual(2, len(files))
        workflow_spec_model = session.query(WorkflowSpecModel).filter_by(id="docx").first()
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
        file_data = session.query(FileDataModel).filter(FileDataModel.file_model_id == files[0].id).first()
        self.assertIsNotNone(file_data.data)
        self.assertTrue(len(file_data.data) > 0)
        # Not going any farther here, assuming this is tested in libraries correctly.

    def test_load_study_information(self):
        """ Test a workflow that includes requests to pull in Study Details."""

        self.load_example_data()
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

    def test_spec_versioning(self):
        self.load_example_data()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("decision_table")
        processor = self.get_processor(study, workflow_spec_model)
        self.assertTrue(processor.get_version_string().startswith('v1.1'))
        file_service = FileService()

        file_service.add_workflow_spec_file(workflow_spec_model, "new_file.txt", "txt", b'blahblah')
        processor = self.get_processor(study, workflow_spec_model)
        self.assertTrue(processor.get_version_string().startswith('v1.1.1'))

        file_path = os.path.join(app.root_path, '..', 'tests', 'data', 'docx', 'docx.bpmn')
        file = open(file_path, "rb")
        data = file.read()

        file_model = db.session.query(FileModel).filter(FileModel.name == "decision_table.bpmn").first()
        file_service.update_file(file_model, data, "txt")
        processor = self.get_processor(study, workflow_spec_model)
        self.assertTrue(processor.get_version_string().startswith('v2.1.1'))


    def test_hard_reset(self):
        self.load_example_data()

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
        self.replace_file("two_forms.bpmn", file_path)

        # Assure that creating a new processor doesn't cause any issues, and maintains the spec version.
        processor.workflow_model.bpmn_workflow_json = processor.serialize()
        processor2 = WorkflowProcessor(processor.workflow_model)
        self.assertFalse(processor2.is_latest_spec) # Still at version 1.

        # Do a hard reset, which should bring us back to the beginning, but retain the data.
        WorkflowProcessor.reset(processor2.workflow_model)
        processor3 = WorkflowProcessor(processor.workflow_model)
        processor3.do_engine_steps()
        self.assertEqual("Step 1", processor3.next_task().task_spec.description)
        self.assertTrue(processor3.is_latest_spec) # Now at version 2.
        task = processor3.next_task()
        task.data = {"color": "blue"}
        processor3.complete_task(task)
        self.assertEqual("New Step", processor3.next_task().task_spec.description)
        self.assertEqual("blue", processor3.next_task().data["color"])


    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_studies')
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_investigators')
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')
    def test_master_bpmn_for_crc(self, mock_details, mock_required_docs, mock_investigators, mock_studies):

        # Mock Protocol Builder response
        studies_response = self.protocol_builder_response('user_studies.json')
        mock_studies.return_value = ProtocolBuilderStudySchema(many=True).loads(studies_response)

        investigators_response = self.protocol_builder_response('investigators.json')
        mock_investigators.return_value = json.loads(investigators_response)

        required_docs_response = self.protocol_builder_response('required_docs.json')
        mock_required_docs.return_value = json.loads(required_docs_response)

        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)

        self.load_example_data(use_crc_data=True)
        app.config['PB_ENABLED'] = True

        study = session.query(StudyModel).first()
        workflow_spec_model = db.session.query(WorkflowSpecModel).\
            filter(WorkflowSpecModel.name == "top_level_workflow").first()
        self.assertIsNotNone(workflow_spec_model)

        processor = self.get_processor(study, workflow_spec_model)
        processor.do_engine_steps()
        self.assertTrue("Top level process is fully automatic.", processor.bpmn_workflow.is_completed())
        data = processor.bpmn_workflow.last_task.data

        logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

        # It should mark Enter Core Data as required, because it is always required.
        self.assertTrue("enter_core_info" in data)
        self.assertEqual("required", data["enter_core_info"])

        # It should mark Personnel as required, because StudyInfo.investigators is not empty.
        self.assertTrue("personnel" in data)
        self.assertEqual("required", data["personnel"])

        # It should mark the sponsor funding source as disabled since the funding required (12) is not included in the required docs.
        self.assertTrue("sponsor_funding_source" in data)
        self.assertEqual("required", data["sponsor_funding_source"])

    def test_enum_with_no_choices_raises_api_error(self):
        self.load_example_data()
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
        self.load_example_data()
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

