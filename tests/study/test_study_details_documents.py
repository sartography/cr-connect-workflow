
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
from crc.scripts.file_data_set import FileDataSet
from crc.services.document_service import DocumentService


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
            filter(FileModel.is_reference is True). \
            filter(FileModel.name == DocumentService.DOCUMENT_LIST).first()
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
        dict = DocumentService.get_dictionary()
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
        docs = StudyInfo().do_task_validate_only(task, study.id, workflow_model.id, "documents")
        self.assertTrue(isinstance(docs, Box))

    @patch('crc.services.protocol_builder.requests.get')
    def test_study_info_returns_document_data_store_values_with_documents(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('required_docs.json')
        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("two_forms")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        file = FileService.add_workflow_file(workflow_id=workflow_model.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234', irb_doc_code=irb_code)
        processor = WorkflowProcessor(workflow_model)
        task = processor.next_task()
        FileDataSet().do_task(task, study.id, workflow_model.id, key="ginger", value="doodle", file_id=file.id)
        docs = StudyInfo().do_task(task, study.id, workflow_model.id, "documents")
        self.assertTrue(isinstance(docs, Box))
        self.assertEquals(1, len(docs.UVACompl_PRCAppr.files))
        self.assertEquals("doodle", docs.UVACompl_PRCAppr.files[0].data_store.ginger)

    @patch('crc.services.protocol_builder.requests.get')
    def test_file_data_set_changes_irb_code(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('required_docs.json')
        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("two_forms")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        file = FileService.add_workflow_file(workflow_id=workflow_model.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234', irb_doc_code=irb_code)
        processor = WorkflowProcessor(workflow_model)
        task = processor.next_task()
        FileDataSet().do_task(task, study.id, workflow_model.id, key="irb_code", value="Study_App_Doc", file_id=file.id)
        docs = StudyInfo().do_task(task, study.id, workflow_model.id, "documents")
        self.assertTrue(isinstance(docs, Box))
        self.assertEquals(1, len(docs.Study_App_Doc.files))
        self.assertEquals("Study_App_Doc", docs.Study_App_Doc.files[0].data_store.irb_code)


    @patch('crc.services.protocol_builder.requests.get')
    def test_file_data_set_invalid_irb_code_fails(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('required_docs.json')
        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("two_forms")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        file = FileService.add_workflow_file(workflow_id=workflow_model.id,
                                      name="anything.png", content_type="text",
                                      binary_data=b'1234', irb_doc_code=irb_code)
        processor = WorkflowProcessor(workflow_model)
        task = processor.next_task()
        with self.assertRaises(ApiError):
            FileDataSet().do_task(task, study.id, workflow_model.id, key="irb_code", value="My_Pretty_Pony",
                              file_id=file.id)
