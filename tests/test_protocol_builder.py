from unittest.mock import patch

from crc import app
from tests.base_test import BaseTest
from crc.services.protocol_builder import ProtocolBuilderService


class TestProtocolBuilder(BaseTest):
    test_uid = "dhf8r"
    test_study_id = 1

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_studies(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('user_studies.json')
        response = ProtocolBuilderService.get_studies(self.test_uid)
        self.assertIsNotNone(response)

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_investigators(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('investigators.json')
        response = ProtocolBuilderService.get_investigators(self.test_study_id)
        self.assertIsNotNone(response)
        self.assertEqual(5, len(response))
        self.assertEqual("DC", response[0]["INVESTIGATORTYPE"])
        self.assertEqual("Department Contact", response[0]["INVESTIGATORTYPEFULL"])
        self.assertEqual("asd3v", response[0]["NETBADGEID"])

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_required_docs(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('required_docs.json')
        response = ProtocolBuilderService.get_required_docs(self.test_study_id)
        self.assertIsNotNone(response)
        self.assertEqual(5, len(response))
        self.assertEqual(6, response[0]['AUXDOCID'])

    @patch('crc.services.protocol_builder.requests.get')
    def test_get_details(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('study_details.json')
        response = ProtocolBuilderService.get_study_details(self.test_study_id)
        self.assertIsNotNone(response)
        self.assertEqual(64, len(response))
        self.assertEqual(1234, response['IND_1'])
