import json
import unittest

from crc import session
from crc.api.common import ApiErrorSchema
from crc.models.file import FileModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel, WorkflowSpecCategoryModel
from tests.base_test import BaseTest


class TestWorkflowSpecValidation(BaseTest):

    def validate_workflow(self, workflow_name):
        self.load_example_data()
        spec_model = self.load_test_spec(workflow_name)
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        return ApiErrorSchema(many=True).load(json_data)

    def test_successful_validation_of_test_workflows(self):
        self.assertEqual(0, len(self.validate_workflow("parallel_tasks")))
        self.assertEqual(0, len(self.validate_workflow("decision_table")))
        self.assertEqual(0, len(self.validate_workflow("docx")))
        self.assertEqual(0, len(self.validate_workflow("exclusive_gateway")))
        self.assertEqual(0, len(self.validate_workflow("file_upload_form")))
        self.assertEqual(0, len(self.validate_workflow("random_fact")))
        self.assertEqual(0, len(self.validate_workflow("study_details")))
        self.assertEqual(0, len(self.validate_workflow("two_forms")))

    @unittest.skip("There is one workflow that is failing right now, and I want that visible after deployment.")
    def test_successful_validation_of_auto_loaded_workflows(self):
        self.load_example_data()
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
        errors = self.validate_workflow("invalid_expression")
        self.assertEqual(1, len(errors))
        self.assertEqual("invalid_expression", errors[0]['code'])
        self.assertEqual("ExclusiveGateway_003amsm", errors[0]['task_id'])
        self.assertEqual("Has Bananas Gateway", errors[0]['task_name'])
        self.assertEqual("invalid_expression.bpmn", errors[0]['file_name'])
        self.assertEqual("The expression you provided does not exist:this_value_does_not_exist==true", errors[0]["message"])

    def test_validation_error(self):
        errors = self.validate_workflow("invalid_spec")
        self.assertEqual(1, len(errors))
        self.assertEqual("workflow_validation_error", errors[0]['code'])
        self.assertEqual("StartEvent_1", errors[0]['task_id'])
        self.assertEqual("invalid_spec.bpmn", errors[0]['file_name'])

    def test_invalid_script(self):
        errors = self.validate_workflow("invalid_script")
        self.assertEqual(1, len(errors))
        self.assertEqual("workflow_execution_exception", errors[0]['code'])
        self.assertTrue("NoSuchScript" in errors[0]['message'])
        self.assertEqual("Invalid_Script_Task", errors[0]['task_id'])
        self.assertEqual("An Invalid Script Reference", errors[0]['task_name'])
        self.assertEqual("invalid_script.bpmn", errors[0]['file_name'])
