import os
from unittest.mock import patch

from crc import app
from crc.models.file import CONTENT_TYPES
from crc.scripts.study_info import StudyInfo
from crc.services.file_service import FileService
from crc.services.protocol_builder import ProtocolBuilderService
from tests.base_test import BaseTest


class TestStudyInfoService(BaseTest):
    test_uid = "dhf8r"
    test_study_id = 1

    """
            1. get a list of only the required documents for the study.
            2. For this study, is this document required accroding to the protocol builder? 
            3. For ALL uploaded documents, what the total number of files that were uploaded? per instance of this document naming
            convention that we are implementing for the IRB.
    """

    def test_get_required_docs(self):
        """The Study info service should re-structure required docs to provide
        a flatted view of just the documents that are required.
        """

    def create_reference_document(self):
        file_path = os.path.join(app.root_path, '..', 'tests', 'data', 'reference', 'irb_documents.xlsx')
        file = open(file_path, "rb")
        FileService.add_reference_file(StudyInfo.IRB_PRO_CATEGORIES_FILE,
                                       binary_data=file.read(),
                                       content_type=CONTENT_TYPES['xls'])


    def test_validate_returns_error_if_reference_files_do_not_exist(self):
        errors = StudyInfo.validate()
        FileService.
        self.assertTrue(len(errors) > 0)
        self.assertEquals("file_not_found", errors[0].code)

    def test_no_validation_error_when_correct_file_exists(self):
        self.create_reference_document()
        errors = StudyInfo.validate()
        self.assertTrue(len(errors) == 0)

    def test_load_lookup_data(self):
        self.create_reference_document()
        dict = StudyInfo().get_file_reference_dictionary()
        self.assertIsNotNone(dict)

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_required_docs(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('required_docs.json')
        self.create_reference_document()
        studyInfo = StudyInfo()
        required_docs = studyInfo.get_required_docs(12)
        self.assertIsNotNone(required_docs)
        self.assertTrue(len(required_docs) == 5)
        self.assertEquals(6, required_docs[0].protocol_builder_id)