import json
import unittest
from unittest.mock import patch

from tests.base_test import BaseTest

from crc import session, app
from crc.api.common import ApiErrorSchema
from crc.models.protocol_builder import ProtocolBuilderStudySchema
from crc.models.workflow import WorkflowSpecModel
from crc.services.workflow_service import WorkflowService


class TestWorkflowSpecValidation(BaseTest):

    def validate_workflow(self, workflow_name):
        spec_model = self.load_test_spec(workflow_name)
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        return ApiErrorSchema(many=True).load(json_data)

    def test_successful_validation_of_test_workflows(self):
        app.config['PB_ENABLED'] = False  # Assure this is disabled.
        self.load_example_data()
        self.assertEqual(0, len(self.validate_workflow("parallel_tasks")))
        self.assertEqual(0, len(self.validate_workflow("decision_table")))
        self.assertEqual(0, len(self.validate_workflow("docx")))
        self.assertEqual(0, len(self.validate_workflow("exclusive_gateway")))
        self.assertEqual(0, len(self.validate_workflow("file_upload_form")))
        self.assertEqual(0, len(self.validate_workflow("random_fact")))
        self.assertEqual(0, len(self.validate_workflow("study_details")))
        self.assertEqual(0, len(self.validate_workflow("two_forms")))

    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_investigators')  # mock_studies
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_required_docs')  # mock_docs
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_study_details')  # mock_details
    @patch('crc.services.protocol_builder.ProtocolBuilderService.get_studies')  # mock_studies
    def test_successful_validation_of_crc_workflows(self, mock_studies, mock_details, mock_docs, mock_investigators):

        # Mock Protocol Builder responses
        studies_response = self.protocol_builder_response('user_studies.json')
        mock_studies.return_value = ProtocolBuilderStudySchema(many=True).loads(studies_response)
        details_response = self.protocol_builder_response('study_details.json')
        mock_details.return_value = json.loads(details_response)
        docs_response = self.protocol_builder_response('required_docs.json')
        mock_docs.return_value = json.loads(docs_response)
        investigators_response = self.protocol_builder_response('investigators.json')
        mock_investigators.return_value = json.loads(investigators_response)

        self.load_example_data(use_crc_data=True)
        app.config['PB_ENABLED'] = True
        self.validate_all_loaded_workflows()


    def validate_all_loaded_workflows(self):
        workflows = session.query(WorkflowSpecModel).all()
        errors = []
        for w in workflows:
            rv = self.app.get('/v1.0/workflow-specification/%s/validate' % w.id,
                              headers=self.logged_in_headers())
            self.assert_success(rv)
            json_data = json.loads(rv.get_data(as_text=True))
            errors.extend(ApiErrorSchema(many=True).load(json_data))
        self.assertEqual(0, len(errors), json.dumps(errors))

    def test_invalid_expression(self):
        self.load_example_data()
        errors = self.validate_workflow("invalid_expression")
        self.assertEqual(2, len(errors))
        self.assertEqual("workflow_validation_exception", errors[0]['code'])
        self.assertEqual("ExclusiveGateway_003amsm", errors[0]['task_id'])
        self.assertEqual("Has Bananas Gateway", errors[0]['task_name'])
        self.assertEqual("invalid_expression.bpmn", errors[0]['file_name'])
        self.assertEqual('When populating all fields ... ExclusiveGateway_003amsm: Error evaluating expression \'this_value_does_not_exist==true\', '
                         'name \'this_value_does_not_exist\' is not defined', errors[0]["message"])
        self.assertIsNotNone(errors[0]['task_data'])
        self.assertIn("has_bananas", errors[0]['task_data'])

    def test_validation_error(self):
        self.load_example_data()
        errors = self.validate_workflow("invalid_spec")
        self.assertEqual(2, len(errors))
        self.assertEqual("workflow_validation_error", errors[0]['code'])
        self.assertEqual("StartEvent_1", errors[0]['task_id'])
        self.assertEqual("invalid_spec.bpmn", errors[0]['file_name'])

    def test_invalid_script(self):
        self.load_example_data()
        errors = self.validate_workflow("invalid_script")
        self.assertEqual(2, len(errors))
        self.assertEqual("workflow_validation_exception", errors[0]['code'])
        self.assertTrue("NoSuchScript" in errors[0]['message'])
        self.assertEqual("Invalid_Script_Task", errors[0]['task_id'])
        self.assertEqual("An Invalid Script Reference", errors[0]['task_name'])
        self.assertEqual("invalid_script.bpmn", errors[0]['file_name'])

    def test_invalid_script2(self):
        self.load_example_data()
        errors = self.validate_workflow("invalid_script2")
        self.assertEqual(2, len(errors))
        self.assertEqual("workflow_validation_exception", errors[0]['code'])
        self.assertEqual("Invalid_Script_Task", errors[0]['task_id'])
        self.assertEqual("An Invalid Script Reference", errors[0]['task_name'])
        self.assertEqual("invalid_script2.bpmn", errors[0]['file_name'])

    def test_repeating_sections_correctly_populated(self):
        self.load_example_data()
        spec_model = self.load_test_spec('repeat_form')
        final_data = WorkflowService.test_spec(spec_model.id)
        self.assertIsNotNone(final_data)
        self.assertIn('cats', final_data)

    def test_required_fields(self):
        self.load_example_data()
        spec_model = self.load_test_spec('required_fields')
        final_data = WorkflowService.test_spec(spec_model.id)
        self.assertIsNotNone(final_data)
        self.assertIn('string_required', final_data)
        self.assertIn('string_not_required', final_data)

        final_data = WorkflowService.test_spec(spec_model.id, required_only=True)
        self.assertIsNotNone(final_data)
        self.assertIn('string_required', final_data)
        self.assertNotIn('string_not_required', final_data)
