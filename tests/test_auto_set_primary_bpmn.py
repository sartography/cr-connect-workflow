from tests.base_test import BaseTest
import io
import json
from crc.models.workflow import WorkflowSpecInfo, WorkflowSpecInfoSchema
from crc.services.workflow_spec_service import WorkflowSpecService


class TestAutoSetPrimaryBPMN(BaseTest):

    def test_auto_set_primary_bpmn(self):
        category = self.assure_category_exists()
        spec = WorkflowSpecInfo(id='make_cookies', display_name='Cooooookies',
                                description='Om nom nom delicious cookies', category_id=category.id,
                                standalone=False)
        rv = self.app.post('/v1.0/workflow-specification',
                           headers=self.logged_in_headers(),
                           content_type="application/json",
                           data=json.dumps(WorkflowSpecInfoSchema().dump(spec)))
        self.assert_success(rv)
        db_spec = WorkflowSpecService().get_spec(spec.id)
        self.assertEqual(spec.display_name, db_spec.display_name)
        self.assertEqual('',db_spec.primary_process_id)
        self.assertEqual('',db_spec.primary_file_name)
        data = {}
        data['file'] = io.BytesIO(self.minimal_bpmn("abcdef")), 'my_new_file.bpmn'

        # Add a new BPMN file to the specification
        rv = self.app.post(f'/v1.0/workflow-specification/{db_spec.id}/file', data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        # Make sure we now have a primary bpmn
        db_spec = WorkflowSpecService().get_spec(spec.id)
        self.assertEqual(db_spec.primary_process_id, '1')
        self.assertEqual(db_spec.primary_file_name, 'my_new_file.bpmn')
