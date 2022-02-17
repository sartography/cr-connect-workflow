from tests.base_test import BaseTest

from crc.services.workflow_service import WorkflowService
from crc.services.workflow_processor import WorkflowProcessor
import json


class TestEmptyEnumList(BaseTest):

    def test_empty_enum_list(self):
        self.load_test_spec('empty_workflow', master_spec=True)
        self.create_reference_document()
        spec_model = self.load_test_spec('enum_empty_list')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        json_data = json.loads(rv.get_data(as_text=True))

        self.assertEqual(json_data[0]['code'], 'invalid_enum')

    def test_default_values_for_enum_as_checkbox(self):
        self.load_test_spec('enum_results')
        workflow = self.create_workflow('enum_results')
        processor = WorkflowProcessor(workflow)
        processor.do_engine_steps()
        task = processor.next_task()
        service = WorkflowService()
        checkbox_enum_field = task.task_spec.form.fields[0]
        radio_enum_field = task.task_spec.form.fields[1]
        self.assertEqual([], service.get_default_value(checkbox_enum_field, task, task.data))
        self.assertEqual(None, service.get_default_value(radio_enum_field, task, task.data))
