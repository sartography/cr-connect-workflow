import json
from unittest.mock import patch

from tests.base_test import BaseTest
from crc import app


class TestGetStudyAssociateValidation(BaseTest):
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_investigators')
    def test_get_study_associate_validation(self, mock):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        response = self.protocol_builder_response('investigators.json')
        mock.return_value = json.loads(response)
        app.config['PB_ENABLED'] = True
        workflow = self.create_workflow('get_study_associate')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % workflow.workflow_spec_id,
                          headers=self.logged_in_headers())
        self.assertEqual(0, len(rv.json))
