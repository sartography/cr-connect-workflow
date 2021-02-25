from unittest.mock import patch
import flask

from crc.api.common import ApiError
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


    def test_study_sponsors_script_validation(self):
        flask.g.user = UserModel(uid='dhf8r')
        self.load_example_data() # study_info script complains if irb_documents.xls is not loaded
                                 # during the validate phase I'm going to assume that we will never
                                 # have a case where irb_documents.xls is not loaded ??

        self.load_test_spec("study_sponsors_associate")
        WorkflowService.test_spec("study_sponsors_associate")  # This would raise errors if it didn't validate


    @patch('crc.services.protocol_builder.requests.get')
    def test_study_sponsors_script(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        flask.g.user = UserModel(uid='dhf8r')
        app.config['PB_ENABLED'] = True

        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("study_sponsors_associate")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        WorkflowService.test_spec("study_sponsors_associate")
        processor = WorkflowProcessor(workflow_model)
        processor.do_engine_steps()
        self.assertTrue(processor.bpmn_workflow.is_completed())
        data = processor.next_task().data
        self.assertIn('sponsors', data)
        self.assertIn('out', data)
        print(data['out'])
        self.assertEquals([{'uid': 'dhf8r', 'role': 'owner', 'send_email': True, 'access': True},
                           {'uid': 'lb3dp', 'role': 'SuperDude', 'send_email': False, 'access': True}]
                           , data['out'])
        self.assertEquals({'uid': 'lb3dp', 'role': 'SuperDude', 'send_email': False, 'access': True}
                          , data['out2'])

        self.assertEquals([{'uid': 'dhf8r', 'role': 'owner', 'send_email': True, 'access': True},
                           {'uid': 'lb3dp', 'role': 'SuperGal', 'send_email': False, 'access': True}]
                           , data['out3'])
        self.assertEquals({'uid': 'lb3dp', 'role': 'SuperGal', 'send_email': False, 'access': True}
                          , data['out4'])


        self.assertEquals(3, len(data['sponsors']))


    @patch('crc.services.protocol_builder.requests.get')
    def test_study_sponsors_script_fail(self, mock_get):
        mock_get.return_value.ok = True
        mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
        flask.g.user = UserModel(uid='dhf8r')
        app.config['PB_ENABLED'] = True

        self.load_example_data()
        self.create_reference_document()
        study = session.query(StudyModel).first()
        workflow_spec_model = self.load_test_spec("study_sponsors_associate_fail")
        workflow_model = StudyService._create_workflow_model(study, workflow_spec_model)
        WorkflowService.test_spec("study_sponsors_associate_fail")
        processor = WorkflowProcessor(workflow_model)
        with self.assertRaises(ApiError):
            processor.do_engine_steps()