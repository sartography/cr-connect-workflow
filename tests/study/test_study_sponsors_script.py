from unittest.mock import patch

from tests.base_test import BaseTest

from crc import session, app
from crc.models.study import StudyModel
from crc.scripts.study_sponsors import StudySponsors
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor
from crc.services.workflow_service import WorkflowService

class TestSudySponsorsScript(BaseTest):
    test_uid = "dhf8r"
    test_study_id = 1

    def test_study_sponsors_script_validation(self):
        self.load_test_spec("study_sponsors")
        WorkflowService.test_spec("study_sponsors")  # This would raise errors if it didn't validate


    @patch('crc.services.protocol_builder.requests.get')
    def test_study_sponsors_script(self, mock_get):

        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        app.config['PB_ENABLED'] = True

        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("study_sponsors")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        WorkflowService.test_spec("study_sponsors")
        processor = WorkflowProcessor(workflow_model)
        processor.do_engine_steps()
        self.assertTrue(processor.bpmn_workflow.is_completed())
        data = processor.next_task().data
        self.assertIn('sponsors', data)
        self.assertEquals(3, len(data['sponsors']))
