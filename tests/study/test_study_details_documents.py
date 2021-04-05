import json

from SpiffWorkflow.bpmn.PythonScriptEngine import Box

from tests.base_test import BaseTest
from unittest.mock import patch

from crc import db, session
from crc.api.common import ApiError
from crc.models.file import FileDataModel, FileModel
from crc.models.protocol_builder import ProtocolBuilderRequiredDocumentSchema
from crc.models.study import StudyModel
from crc.scripts.study_info import StudyInfo
from crc.services.file_service import FileService
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor


class TestStudyDetailsDocumentsScript(BaseTest):
    test_uid = "dhf8r"
    test_study_id = 1

    """
            1. get a list of all documents related to the study.
            2. For this study, is this document required accroding to the protocol builder?
            3. For ALL uploaded documents, what the total number of files that were uploaded? per instance of this document naming
            convention that we are implementing for the IRB.
    """

    @patch('crc.services.protocol_builder.requests.get')
    def test_validate_returns_error_if_reference_files_do_not_exist(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('required_docs.json')

        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("two_forms")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        processor = WorkflowProcessor(workflow_model)
        task = processor.next_task()

        # Remove the reference file.
        file_model = db.session.query(FileModel). \
            filter(FileModel.is_reference == True). \
            filter(FileModel.name == FileService.DOCUMENT_LIST).first()
        if file_model:
            db.session.query(FileDataModel).filter(FileDataModel.file_model_id == file_model.id).delete()
            db.session.query(FileModel).filter(FileModel.id == file_model.id).delete()
        db.session.commit()
        db.session.flush()

        with self.assertRaises(ApiError):
            StudyInfo().do_task_validate_only(task, study.id, "documents")

    @patch('crc.services.protocol_builder.requests.get')
    def test_no_validation_error_when_correct_file_exists(self, mock_get):

        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('required_docs.json')

        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("two_forms")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        processor = WorkflowProcessor(workflow_model)
        task = processor.next_task()
        StudyInfo().do_task_validate_only(task, study.id, workflow_model.id, "documents")

    def test_load_lookup_data(self):
        self.create_reference_document()
        dict = FileService.get_reference_data(FileService.DOCUMENT_LIST, 'code', ['id'])
        self.assertIsNotNone(dict)

    def get_required_docs(self):
        string_data = self.protocol_builder_response('required_docs.json')
        return ProtocolBuilderRequiredDocumentSchema(many=True).loads(string_data)

    @patch('crc.services.protocol_builder.requests.get')
    def test_study_info_returns_a_box_object(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('required_docs.json')
        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("two_forms")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        processor = WorkflowProcessor(workflow_model)
        task = processor.next_task()
        docs = StudyInfo().do_task(task, study.id, workflow_model.id, "documents")
        self.assertTrue(isinstance(docs, Box))