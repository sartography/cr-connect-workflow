import json

from SpiffWorkflow.bpmn.PythonScriptEngine import Box

from tests.base_test import BaseTest
from unittest.mock import patch

from crc import app, session
from crc.models.study import StudyModel
from crc.scripts.study_info import StudyInfo
from crc.services.study_service import StudyService
from crc.services.workflow_processor import WorkflowProcessor


class TestStudyDetailsScript(BaseTest):
    test_uid = "dhf8r"
    test_study_id = 1

    def setUp(self):
        self.load_example_data()
        # self.create_reference_document()
        self.study = session.query(StudyModel).first()
        self.workflow_spec_model = self.load_test_spec("two_forms")
        self.workflow_model = StudyService._create_workflow_model(self.study, self.workflow_spec_model)
        self.processor = WorkflowProcessor(self.workflow_model)
        self.task = self.processor.next_task()

    @patch('crc.services.protocol_builder.requests.get')
    def test_study_info_returns_a_box_object_for_all_validations(self, mock_get):
        app.config['PB_ENABLED'] = True
        mock_get.return_value.ok = True
        for option in StudyInfo.type_options:
            if option == 'info':
                mock_get.return_value.text = self.protocol_builder_response('irb_info.json')
            elif option == 'investigators':
                mock_get.return_value.text = self.protocol_builder_response('investigators.json')
            elif option == 'roles':
                mock_get.return_value.text = self.protocol_builder_response('investigators.json')
            elif option == 'details':
                mock_get.return_value.text = self.protocol_builder_response('study_details.json')
            elif option == 'documents':
                mock_get.return_value.text = self.protocol_builder_response('required_docs.json')
            elif option == 'sponsors':
                mock_get.return_value.text = self.protocol_builder_response('sponsors.json')
            data = StudyInfo().do_task_validate_only(self.task, self.study.id, self.workflow_model.id, option)
            if isinstance(data, list):
                for x in data:
                    self.assertIsInstance(x, Box, "this is not a list of boxes:" + option)
            else:
                self.assertIsInstance(data, Box, "this is not a box:" + option)

    def test_study_info_returns_a_box_object(self):
        docs = StudyInfo().do_task(self.task, self.study.id, self.workflow_model.id, "info")
        self.assertTrue(isinstance(docs, Box))

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_investigators')  # mock_studies
    def test_study_investigators_returns_box(self, mock_investigators):
        investigators_response = self.protocol_builder_response('investigators.json')
        mock_investigators.return_value = json.loads(investigators_response)
        docs = StudyInfo().do_task(self.task, self.study.id, self.workflow_model.id, "investigators")
        self.assertTrue(isinstance(docs, Box))

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_investigators')  # mock_studies
    def test_study_roles_returns_box(self, mock_investigators):
        investigators_response = self.protocol_builder_response('investigators.json')
        mock_investigators.return_value = json.loads(investigators_response)
        docs = StudyInfo().do_task(self.task, self.study.id, self.workflow_model.id, "roles")
        self.assertTrue(isinstance(docs, Box))

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_studies
    def test_study_details_returns_box(self, mock_details):
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)
        data = StudyInfo().do_task(self.task, self.study.id, self.workflow_model.id, "details")
        self.assertTrue(isinstance(data, Box))

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_sponsors')  # mock_studies
    def test_study_sponsors_returns_box(self, mock):
        response = self.protocol_builder_response('sponsors.json')
        mock.return_value = json.loads(response)
        data = StudyInfo().do_task(self.task, self.study.id, self.workflow_model.id, "sponsors")
        self.assertTrue(isinstance(data, list))
        for x in data:
            self.assertIsInstance(x, Box)
