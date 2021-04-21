from tests.base_test import BaseTest
from crc import session
from crc.models.file import FileModel, FileType
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowSpecCategoryModel
import io
import json


class TestAutoSetPrimaryBPMN(BaseTest):

    def test_auto_set_primary_bpmn(self):
        self.load_example_data()
        category_id = session.query(WorkflowSpecCategoryModel).first().id
        # Add a workflow spec
        spec = WorkflowSpecModel(id='make_cookies', name='make_cookies', display_name='Cooooookies',
                                 description='Om nom nom delicious cookies', category_id=category_id)
        rv = self.app.post('/v1.0/workflow-specification',
                           headers=self.logged_in_headers(),
                           content_type="application/json",
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        self.assert_success(rv)
        # grab the spec from the db
        db_spec = session.query(WorkflowSpecModel).filter_by(id='make_cookies').first()
        self.assertEqual(spec.display_name, db_spec.display_name)
        # Make sure we don't already have a primary bpmn file
        have_primary = FileModel.query.filter(FileModel.workflow_spec_id==db_spec.id, FileModel.type==FileType.bpmn, FileModel.primary==True).all()
        self.assertEqual(have_primary, [])
        data = {}
        data['file'] = io.BytesIO(self.minimal_bpmn("abcdef")), 'my_new_file.bpmn'

        # Add a new BPMN file to the specification
        rv = self.app.post('/v1.0/file?workflow_spec_id=%s' % db_spec.id, data=data, follow_redirects=True,
                           content_type='multipart/form-data', headers=self.logged_in_headers())
        self.assert_success(rv)
        file_id = rv.json['id']
        # Make sure we now have a primary bpmn
        have_primary = FileModel.query.filter(FileModel.workflow_spec_id==db_spec.id, FileModel.type==FileType.bpmn, FileModel.primary==True).all()
        self.assertEqual(len(have_primary), 1)
        self.assertEqual(file_id, have_primary[0].id)
