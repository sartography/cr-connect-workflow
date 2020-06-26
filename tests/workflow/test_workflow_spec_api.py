import json

from tests.base_test import BaseTest
from crc import session
from crc.models.file import FileModel
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowModel, WorkflowSpecCategoryModel


class TestWorkflowSpec(BaseTest):

    def test_list_workflow_specifications(self):
        self.load_example_data()
        spec = session.query(WorkflowSpecModel).first()
        rv = self.app.get('/v1.0/workflow-specification',
                          follow_redirects=True,
                          content_type="application/json",headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        specs = WorkflowSpecModelSchema(many=True).load(json_data, session=session)
        spec2 = specs[0]
        self.assertEqual(spec.id, spec2.id)
        self.assertEqual(spec.display_name, spec2.display_name)
        self.assertEqual(spec.description, spec2.description)

    def test_add_new_workflow_specification(self):
        self.load_example_data()
        num_before = session.query(WorkflowSpecModel).count()
        spec = WorkflowSpecModel(id='make_cookies', name='make_cookies', display_name='Cooooookies',
                                 description='Om nom nom delicious cookies')
        rv = self.app.post('/v1.0/workflow-specification',
                           headers=self.logged_in_headers(),
                           content_type="application/json",
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        self.assert_success(rv)
        db_spec = session.query(WorkflowSpecModel).filter_by(id='make_cookies').first()
        self.assertEqual(spec.display_name, db_spec.display_name)
        num_after = session.query(WorkflowSpecModel).count()
        self.assertEqual(num_after, num_before + 1)

    def test_get_workflow_specification(self):
        self.load_example_data()
        db_spec = session.query(WorkflowSpecModel).first()
        rv = self.app.get('/v1.0/workflow-specification/%s' % db_spec.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        api_spec = WorkflowSpecModelSchema().load(json_data, session=session)
        self.assertEqual(db_spec, api_spec)

    def test_update_workflow_specification(self):
        self.load_example_data()

        category_id = 99
        category = WorkflowSpecCategoryModel(id=category_id, name='trap', display_name="It's a trap!", display_order=0)
        session.add(category)
        session.commit()

        db_spec_before: WorkflowSpecModel = session.query(WorkflowSpecModel).first()
        spec_id = db_spec_before.id
        self.assertNotEqual(db_spec_before.category_id, category_id)

        db_spec_before.category_id = category_id
        rv = self.app.put('/v1.0/workflow-specification/%s' % spec_id,
                          content_type="application/json",
                          headers=self.logged_in_headers(),
                          data=json.dumps(WorkflowSpecModelSchema().dump(db_spec_before)))
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        api_spec = WorkflowSpecModelSchema().load(json_data, session=session)
        self.assertEqual(db_spec_before, api_spec)

        db_spec_after: WorkflowSpecModel = session.query(WorkflowSpecModel).filter_by(id=spec_id).first()
        self.assertIsNotNone(db_spec_after.category_id)
        self.assertIsNotNone(db_spec_after.category)
        self.assertEqual(db_spec_after.category.display_name, category.display_name)
        self.assertEqual(db_spec_after.category.display_order, category.display_order)

    def test_delete_workflow_specification(self):
        self.load_example_data()
        spec_id = 'random_fact'
        self.load_test_spec(spec_id)
        num_specs_before = session.query(WorkflowSpecModel).filter_by(id=spec_id).count()
        self.assertEqual(num_specs_before, 1)

        num_files_before = session.query(FileModel).filter_by(workflow_spec_id=spec_id).count()
        num_workflows_before = session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id).count()
        self.assertGreater(num_files_before + num_workflows_before, 0)

        rv = self.app.delete('/v1.0/workflow-specification/' + spec_id, headers=self.logged_in_headers())
        self.assert_success(rv)

        num_specs_after = session.query(WorkflowSpecModel).filter_by(id=spec_id).count()
        self.assertEqual(0, num_specs_after)

        # Make sure that all items in the database with the workflow spec ID are deleted as well.
        num_files_after = session.query(FileModel).filter_by(workflow_spec_id=spec_id).count()
        num_workflows_after = session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id).count()
        self.assertEqual(num_files_after + num_workflows_after, 0)

