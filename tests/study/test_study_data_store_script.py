from unittest.mock import patch
import flask


from tests.base_test import BaseTest

from crc import session, app
from crc.models.study import StudyModel
from crc.models.user import UserModel
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService

class TestSudySponsorsScript(BaseTest):
    test_uid = "dhf8r"
    test_study_id = 1


    @patch('crc.services.protocol_builder.requests.get')
    def test_study_sponsors_script_validation(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        app.config['PB_ENABLED'] = True
        flask.g.user = UserModel(uid='dhf8r')

        self.load_test_spec("study_sponsors_data_store")
        WorkflowService.test_spec("study_sponsors_data_store")  # This would raise errors if it didn't validate


    @patch('crc.services.protocol_builder.requests.get')
    def test_study_sponsors_script(self, mock_get):

        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        flask.g.user = UserModel(uid='dhf8r')
        app.config['PB_ENABLED'] = True

        self.add_studies()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("study_sponsors_data_store")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        WorkflowService.test_spec("study_sponsors_data_store")
        processor = WorkflowProcessor(workflow_model)
        processor.do_engine_steps()
        self.assertTrue(processor.bpmn_workflow.is_completed())
        data = processor.next_task().data
        self.assertIn('sponsors', data)
        self.assertIn('out', data)
        self.assertEqual('empty', data['empty'])
        self.assertEqual('newval', data['out'])
        self.assertEqual(3, len(data['sponsors']))
