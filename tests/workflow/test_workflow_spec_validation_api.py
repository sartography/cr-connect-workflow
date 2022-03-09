import json
import time

from SpiffWorkflow.util.metrics import timeit
from unittest.mock import patch

from tests.base_test import BaseTest

from crc import session, app
from crc.api.common import ApiErrorSchema
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowModel, WorkflowSpecInfo
from crc.services.workflow_service import WorkflowService


class TestWorkflowSpecValidation(BaseTest):

    def validate_workflow(self, workflow_name):
        spec_model = self.load_test_spec(workflow_name)
        total_workflows = session.query(WorkflowModel).count()
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        total_workflows_after = session.query(WorkflowModel).count()
        self.assertEqual(total_workflows, total_workflows_after, "No rogue workflow exists after validation.")
        json_data = json.loads(rv.get_data(as_text=True))

        return ApiErrorSchema(many=True).load(json_data)

    def test_stupid_slow_file_upload_form(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        self.assertEqual(0, len(self.validate_workflow("file_upload_form")))


    def test_successful_validation_of_test_workflows(self):
        app.config['PB_ENABLED'] = False  # Assure this is disabled.
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        self.assertEqual(0, len(self.validate_workflow("parallel_tasks")))
        self.assertEqual(0, len(self.validate_workflow("decision_table")))
        self.assertEqual(0, len(self.validate_workflow("docx")))
        self.assertEqual(0, len(self.validate_workflow("exclusive_gateway")))
        self.assertEqual(0, len(self.validate_workflow("random_fact")))
        self.assertEqual(0, len(self.validate_workflow("study_details")))
        self.assertEqual(0, len(self.validate_workflow("two_forms")))
        self.assertEqual(0, len(self.validate_workflow("ldap_lookup")))

    def test_invalid_expression(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        errors = self.validate_workflow("invalid_expression")
        self.assertEqual(1, len(errors))
        self.assertEqual("workflow_validation_exception", errors[0]['code'])
        self.assertEqual("ExclusiveGateway_003amsm", errors[0]['task_id'])
        self.assertEqual("Has Bananas Gateway", errors[0]['task_name'])
        self.assertEqual("invalid_expression.bpmn", errors[0]['file_name'])
        self.assertEqual('ExclusiveGateway_003amsm: Error evaluating expression \'this_value_does_not_exist==true\', '
                         'name \'this_value_does_not_exist\' is not defined', errors[0]["message"])
        self.assertIsNotNone(errors[0]['task_data'])
        self.assertIn("has_bananas", errors[0]['task_data'])

    def test_validation_error(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        errors = self.validate_workflow("invalid_spec")
        self.assertEqual(1, len(errors))
        self.assertEqual("workflow_validation_error", errors[0]['code'])
        self.assertEqual("StartEvent_1", errors[0]['task_id'])
        self.assertEqual("invalid_spec.bpmn", errors[0]['file_name'])


    def test_invalid_script(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        errors = self.validate_workflow("invalid_script")
        self.assertEqual(1, len(errors))
        self.assertEqual("workflow_validation_exception", errors[0]['code'])
        #self.assertTrue("NoSuchScript" in errors[0]['message'])
        self.assertEqual("Invalid_Script_Task", errors[0]['task_id'])
        self.assertEqual("An Invalid Script Reference", errors[0]['task_name'])
        self.assertEqual("invalid_script.bpmn", errors[0]['file_name'])

    def test_invalid_script2(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        errors = self.validate_workflow("invalid_script2")
        self.assertEqual(1, len(errors))
        self.assertEqual("workflow_validation_exception", errors[0]['code'])
        self.assertEqual("Invalid_Script_Task", errors[0]['task_id'])
        self.assertEqual(3, errors[0]['line_number'])
        self.assertEqual(9, errors[0]['offset'])
        self.assertEqual("SyntaxError", errors[0]['error_type'])
        self.assertEqual("A Syntax Error", errors[0]['task_name'])
        self.assertEqual("invalid_script2.bpmn", errors[0]['file_name'])

    def test_invalid_script3(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        errors = self.validate_workflow("invalid_script3")
        self.assertEqual(1, len(errors))
        self.assertEqual("Invalid_Script_Task", errors[0]['task_id'])
        self.assertEqual(3, errors[0]['line_number'])
        self.assertEqual("NameError", errors[0]['error_type'])

    def test_repeating_sections_correctly_populated(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('repeat_form')
        final_data = WorkflowService.test_spec(spec_model.id)
        self.assertIsNotNone(final_data)
        self.assertIn('cats', final_data)

    def test_required_fields(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('required_fields')
        final_data = WorkflowService.test_spec(spec_model.id)
        self.assertIsNotNone(final_data)
        self.assertIn('string_required', final_data)
        self.assertIn('string_not_required', final_data)

        final_data = WorkflowService.test_spec(spec_model.id, required_only=True)
        self.assertIsNotNone(final_data)
        self.assertIn('string_required', final_data)
        self.assertNotIn('string_not_required', final_data)

    def test_enum_defaults_correctly_populated(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('required_fields')
        final_data = WorkflowService.test_spec(spec_model.id, required_only=True)
        self.assertIsNotNone(final_data)
        self.assertIn('enum_with_default', final_data)
        self.assertEqual('maybe', final_data['enum_with_default'])

    def test_invalid_custom_field(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        errors = self.validate_workflow("invalid_custom_field")
        self.assertEqual(1, len(errors))
        self.assertEqual("invalid_field_type", errors[0]['code'])

    @patch('crc.services.workflow_processor.WorkflowProcessor.run_master_spec')
    def test_disabled_spec_validation(self, mock_status):
        """A disabled workflow spec should fail validation"""
        app.config['PB_ENABLED'] = True
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec = self.load_test_spec('data_security_plan')
        workflow = self.create_workflow('data_security_plan')
        study_model = session.query(StudyModel).first()

        # This response sets the status for data_security_plan to disabled
        status_response = self.protocol_builder_response('_get_study_status.json')
        mock_status.return_value = json.loads(status_response)[0]

        # This should raise an ApiError which we can see in the json data
        rv = self.app.get('/v1.0/workflow-specification/%s/validate?study_id=%s' % (spec.id, study_model.id), headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data())
        self.assertEqual(1, len(json_data))
        api_error = json_data[0]
        self.assertEqual('disabled_workflow', api_error['code'])
        self.assertEqual('This workflow is disabled. This is my mocked disable message.', api_error['message'])


    def test_date_generation_during_validation(self):
        # We hit a bug where the date was generated as a part of a value_expression during validation, but
        # it wasn't converted to an ISO String as it would be if submitted through the API.
        # subsequent attempts to work with the expected date_string failed, because it was already a date.
        # This can't happen in the front end code base, but it was breaking validation.
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        errors = self.validate_workflow("date_value_expression")
        self.assertEqual(0, len(errors))

    def test_fields_required_based_on_later_fields_correctly_populates(self):
        """Say you have a form, where the first field is required only if the
        SECOND field is checked true.  This assures such a case will validate and
        that the variables that should exist (because they are required) do exist.

        As a bonus test, we also assert that a default field is always present
        regardless of it's hidden status.
        """
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        errors = self.validate_workflow("required_expressions")
        self.assertEqual(0, len(errors))

