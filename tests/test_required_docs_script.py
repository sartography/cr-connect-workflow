from unittest.mock import patch

from crc import db
from crc.models.file import FileDataModel, FileModel
from crc.scripts.required_docs import RequiredDocs
from crc.services.file_service import FileService
from tests.base_test import BaseTest


class TestRequiredDocsScript(BaseTest):
    test_uid = "dhf8r"
    test_study_id = 1

    """
            1. get a list of only the required documents for the study.
            2. For this study, is this document required accroding to the protocol builder? 
            3. For ALL uploaded documents, what the total number of files that were uploaded? per instance of this document naming
            convention that we are implementing for the IRB.
    """

    def test_validate_returns_error_if_reference_files_do_not_exist(self):
        file_model = db.session.query(FileModel). \
            filter(FileModel.is_reference == True). \
            filter(FileModel.name == FileService.IRB_PRO_CATEGORIES_FILE).first()
        if file_model:
            db.session.query(FileDataModel).filter(FileDataModel.file_model_id == file_model.id).delete()
            db.session.query(FileModel).filter(FileModel.id == file_model.id).delete()
        db.session.commit()
        db.session.flush()
        errors = RequiredDocs.validate()
        self.assertTrue(len(errors) > 0)
        self.assertEquals("file_not_found", errors[0].code)

    def test_no_validation_error_when_correct_file_exists(self):
        self.create_reference_document()
        errors = RequiredDocs.validate()
        self.assertTrue(len(errors) == 0)

    def test_load_lookup_data(self):
        self.create_reference_document()
        dict = FileService.get_file_reference_dictionary()
        self.assertIsNotNone(dict)

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_required_docs(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('required_docs.json')
        self.create_reference_document()
        script = RequiredDocs()
        required_docs = script.get_required_docs(12)  # Mocked out, any random study id works.
        self.assertIsNotNone(required_docs)
        self.assertTrue(6 in required_docs.keys())
        self.assertEquals("Cancer Center's PRC Approval Form", required_docs[6]['name'])
        self.assertEquals("UVA Compliance", required_docs[6]['category1'])
        self.assertEquals("PRC Approval", required_docs[6]['category2'])
        self.assertEquals("CRC", required_docs[6]['Who Uploads?'])
        self.assertEquals(0, required_docs[6]['count'])

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_required_docs_has_correct_count_when_a_file_exists(self, mock_get):
        self.load_example_data()

        # Mock out the protocol builder
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('required_docs.json')

        # Make sure the xslt reference document is in place.
        self.create_reference_document()
        script = RequiredDocs()

        # Add a document to the study with the correct code.
        workflow = self.create_workflow('docx')
        irb_code = "UVACompliance.PRCApproval"  # The first file referenced in pb required docs.
        FileService.add_task_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  task_id="fakingthisout",
                                  name="anything.png", content_type="text",
                                  binary_data=b'1234', irb_doc_code=irb_code)

        required_docs = script.get_required_docs(workflow.study_id)
        self.assertIsNotNone(required_docs)
        self.assertEquals(1, required_docs[6]['count'])
