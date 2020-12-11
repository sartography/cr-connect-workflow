from unittest.mock import patch

from crc import app
from tests.base_test import BaseTest
from crc.api.workflow_sync import get_all_spec_state, get_changed_workflows
import json
pip

class TestWorkflowSync(BaseTest):

    @patch('crc.api.workflow_sync.requests.get')
    def test_get_no_changes(self, mock_get):
        othersys = get_all_spec_state()
        mock_get.return_value.ok = True
        mock_get.return_value.text = json.dumps(othersys)
        response = get_changed_workflows('somewhere over the rainbow')
        self.assertIsNotNone(response)
        self.assertEqual(response,[])

