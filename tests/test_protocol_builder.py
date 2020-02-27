from unittest.mock import patch

from crc.services.protocol_builder import ProtocolBuilderService
from tests.base_test import BaseTest


class TestProtocolBuilder(BaseTest):
    test_uid = "dhf8r"
    test_study_id = 1

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_studies(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('user_studies.json')
        response = ProtocolBuilderService.get_studies(self.test_uid)
        self.assertIsNotNone(response)

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_investigators(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('investigators.json')
        response = ProtocolBuilderService.get_investigators(self.test_study_id)
        self.assertIsNotNone(response)

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_required_docs(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('required_docs.json')
        response = ProtocolBuilderService.get_required_docs(self.test_study_id)
        self.assertIsNotNone(response)

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_details(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('study_details.json')
        response = ProtocolBuilderService.get_study_details(self.test_study_id)
        self.assertIsNotNone(response)
