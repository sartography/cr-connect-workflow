from tests.base_test import BaseTest
from crc import session
from crc.models.file import FileModel, FileType
import io
import json


class TestAutoSetPrimaryBPMN(BaseTest):

    def test_auto_set_primary_bpmn(self):
        self.load_example_data()
        category = self.assure_category_exists()
        # Add a workflow spec
        spec = WorkflowSpecModel(id='make_cookies', display_name='Cooooookies',
                                 description='Om nom nom delicious cookies', category_id=category.id,
                                 standalone=False)
        rv = self.app.post('/v1.0/workflow-specification',
                           headers=self.logged_in_headers(),
                           content_type="application/json",
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        self.assert_success(rv)
        # grab the spec from the db
        db_spec = session.query(WorkflowSpecModel).filter_by(id='make_cookies').first()
        self.assertEqual(spec.display_name, db_spec.display_name)
        self.assertIsNone(db_spec.primary_process_id)
        self.assertIsNone(db_spec.primary_file_name)
        data = {}
        data['file'] = io.BytesIO(self.minimal_bpmn("abcdef")), 'my_new_file.bpmn'

        # Add a new BPMN file to the specification
        rv = self.app.post(f'/v1.0/workflow-specification/{db_spec.id}/file', data=data,
                           follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        # Make sure we now have a primary bpmn
        db_spec = session.query(WorkflowSpecModel).filter_by(id='make_cookies').first()
        self.assertEqual(db_spec.primary_process_id, '1')
        self.assertEqual(db_spec.primary_file_name, 'my_new_file.bpmn')
