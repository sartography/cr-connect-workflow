import json
from unittest.mock import patch

from crc import db
from crc.models.file import FileDataModel, FileModel
from crc.models.protocol_builder import ProtocolBuilderRequiredDocumentSchema
from crc.scripts.documents import Documents
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
        errors = Documents.validate()
        self.assertTrue(len(errors) > 0)
        self.assertEqual("file_not_found", errors[0].code)

    def test_no_validation_error_when_correct_file_exists(self):
        self.create_reference_document()
        errors = Documents.validate()
        self.assertTrue(len(errors) == 0)

    def test_load_lookup_data(self):
        self.create_reference_document()
        dict = FileService.get_file_reference_dictionary()
        self.assertIsNotNone(dict)

    def get_required_docs(self):
        string_data = self.protocol_builder_response('required_docs.json')
        return ProtocolBuilderRequiredDocumentSchema(many=True).loads(string_data)

    def test_get_required_docs(self):
        pb_docs = self.get_required_docs()
        self.create_reference_document()
        script = Documents()
        documents = script.get_documents(12, pb_docs)  # Mocked out, any random study id works.
        self.assertIsNotNone(documents)
        self.assertTrue("UVACompl_PRCAppr" in documents.keys())
        self.assertEqual("Cancer Center's PRC Approval Form", documents["UVACompl_PRCAppr"]['Name'])
        self.assertEqual("UVA Compliance", documents["UVACompl_PRCAppr"]['category1'])
        self.assertEqual("PRC Approval", documents["UVACompl_PRCAppr"]['category2'])
        self.assertEqual("CRC", documents["UVACompl_PRCAppr"]['Who Uploads?'])
        self.assertEqual(0, documents["UVACompl_PRCAppr"]['count'])
        self.assertEqual(True, documents["UVACompl_PRCAppr"]['required'])
        self.assertEqual('6', documents["UVACompl_PRCAppr"]['Id'])

    def test_get_required_docs_has_correct_count_when_a_file_exists(self):
        self.load_example_data()
        pb_docs = self.get_required_docs()
        # Make sure the xslt reference document is in place.
        self.create_reference_document()
        script = Documents()

        # Add a document to the study with the correct code.
        workflow = self.create_workflow('docx')
        irb_code = "UVACompl_PRCAppr"  # The first file referenced in pb required docs.
        FileService.add_task_file(study_id=workflow.study_id, workflow_id=workflow.id,
                                  task_id="fakingthisout",
                                  name="anything.png", content_type="text",
                                  binary_data=b'1234', irb_doc_code=irb_code)

        docs = script.get_documents(workflow.study_id, pb_docs)
        self.assertIsNotNone(docs)
        self.assertEqual(1, docs["UVACompl_PRCAppr"]['count'])
