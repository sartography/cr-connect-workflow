from tests.base_test import BaseTest

from crc.scripts.enum_label import EnumLabel
from flask_bpmn.api.common import ApiError
from crc.services.workflow_processor import WorkflowProcessor


class TestGetEnumLabel(BaseTest):

    def setUp(self):
        self.workflow = self.create_workflow('enum_options_all')
        self.workflow_api = self.get_workflow_api(self.workflow)

        # Assure the form has been loaded at least once.
        processor = WorkflowProcessor(self.workflow)
        processor.do_engine_steps()
        self.task = processor.next_task()
        self.assertEqual(self.task.get_name(), 'myFormTask')

        self.labelScript = EnumLabel()

    def test_get_enum_label_for_ldap(self):
        result = self.labelScript.do_task(self.task, self.workflow_api.study_id, self.workflow_api.id,
                            task='myFormTask', field='ldap', value='dhf8r')
        self.assertEqual("Dan Funk", result)

    def test_get_enum_label_for_standard_enum(self):
        result = self.labelScript.do_task(self.task, self.workflow_api.study_id, self.workflow_api.id,
                            task='myFormTask', field='standard_enum', value='one')
        self.assertEqual('1', result)

    def test_get_enum_label_using_unnamed_args(self):
        result = self.labelScript.do_task(self.task, self.workflow_api.study_id, self.workflow_api.id,
                            'myFormTask', 'standard_enum', 'one')
        self.assertEqual('1', result)

    def test_get_enum_label_for_spreadsheet(self):
        result = self.labelScript.do_task(self.task, self.workflow_api.study_id, self.workflow_api.id,
                            task='myFormTask', field='spreadsheet', value='2')
        self.assertEqual('T-shirts', result)

    def test_get_enum_label_for_data(self):
        result = self.labelScript.do_task(self.task, self.workflow_api.study_id, self.workflow_api.id,
                            task='myFormTask', field='data', value='simo')
        self.assertEqual('Simo', result)

    def test_get_enum_label_for_checkbox(self):
        result = self.labelScript.do_task(self.task, self.workflow_api.study_id, self.workflow_api.id,
                            task='myFormTask', field='checkbox', value='simo')
        self.assertEqual('Simo', result)


    def test_get_invalid_spec_name(self):
        with self.assertRaises(ApiError) as ctx:
            ldap_result = self.labelScript.do_task(self.task, self.workflow_api.study_id, self.workflow_api.id,
                            task='myWrongFormTask', field='standard_enum', value='one')
        self.assertEqual("ApiError: Unable to find a task in the workflow called 'myWrongFormTask'. ", str(ctx.exception))

    def test_get_invalid_field_name(self):
        with self.assertRaises(ApiError) as ctx:
            ldap_result = self.labelScript.do_task(self.task, self.workflow_api.study_id, self.workflow_api.id,
                            task='myFormTask', field='made_up_enum', value='one')
        self.assertEqual("ApiError: The task 'myFormTask' has no field named 'made_up_enum'. ", str(ctx.exception))
