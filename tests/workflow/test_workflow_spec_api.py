import json
import os.path

from tests.base_test import BaseTest
from crc import session
from crc.models.file import FileModel
from crc.models.workflow import WorkflowModel
from crc.services.spec_file_service import SpecFileService

from example_data import ExampleDataLoader


class TestWorkflowSpec(BaseTest):

    def test_list_workflow_specifications(self):
        self.load_example_data()
        self.load_test_spec('random_fact')
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
        self.load_test_spec('random_fact')
        num_before = session.query(WorkflowSpecModel).count()
        category_id = session.query(WorkflowSpecCategoryModel).first().id
        category_count = session.query(WorkflowSpecModel).filter_by(category_id=category_id).count()
        spec = WorkflowSpecModel(id='make_cookies', display_name='Cooooookies',
                                 description='Om nom nom delicious cookies', category_id=category_id,
                                 standalone=False)
        rv = self.app.post('/v1.0/workflow-specification',
                           headers=self.logged_in_headers(),
                           content_type="application/json",
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        self.assert_success(rv)
        db_spec = session.query(WorkflowSpecModel).filter_by(id='make_cookies').first()
        self.assertEqual(spec.display_name, db_spec.display_name)
        num_after = session.query(WorkflowSpecModel).count()
        self.assertEqual(num_after, num_before + 1)
        self.assertEqual(category_count, db_spec.display_order)
        category_count_after = session.query(WorkflowSpecModel).filter_by(category_id=category_id).count()
        self.assertEqual(category_count_after, category_count + 1)

    def test_get_workflow_specification(self):
        self.load_example_data()
        self.load_test_spec('random_fact')
        db_spec = session.query(WorkflowSpecModel).first()
        rv = self.app.get('/v1.0/workflow-specification/%s' % db_spec.id, headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        api_spec = WorkflowSpecModelSchema().load(json_data, session=session)
        self.assertEqual(db_spec, api_spec)

    def test_update_workflow_specification(self):
        self.load_example_data()
        self.load_test_spec('random_fact')
        category_id = 99
        category = WorkflowSpecCategoryModel(id=category_id, display_name="It's a trap!", display_order=0)
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
        spec = self.load_test_spec(spec_id)
        workflow = self.create_workflow(spec_id)
        workflow_api = self.get_workflow_api(workflow)
        workflow_path = SpecFileService.workflow_path(spec)

        num_specs_before = session.query(WorkflowSpecModel).filter_by(id=spec_id).count()
        self.assertEqual(num_specs_before, 1)

        num_files_before = len(SpecFileService.get_files(spec))
        num_workflows_before = session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id).count()
        self.assertGreater(num_files_before + num_workflows_before, 0)

        rv = self.app.delete('/v1.0/workflow-specification/' + spec_id, headers=self.logged_in_headers())
        self.assert_success(rv)

        num_specs_after = session.query(WorkflowSpecModel).filter_by(id=spec_id).count()
        self.assertEqual(0, num_specs_after)

        # Make sure that all items in the database and file system are deleted as well.
        self.assertFalse(os.path.exists(workflow_path))
        num_workflows_after = session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id).count()
        self.assertEqual(num_workflows_after, 0)

    def test_display_order_after_delete_spec(self):
        self.load_example_data()
        self.load_test_spec('random_fact')
        workflow_spec_category = session.query(WorkflowSpecCategoryModel).first()
        spec_model_1 = WorkflowSpecModel(id='test_spec_1', display_name='Test Spec 1',
                                         description='Test Spec 1 Description', category_id=workflow_spec_category.id,
                                         display_order=1, standalone=False)
        spec_model_2 = WorkflowSpecModel(id='test_spec_2', display_name='Test Spec 2',
                                         description='Test Spec 2 Description', category_id=workflow_spec_category.id,
                                         display_order=2, standalone=False)
        spec_model_3 = WorkflowSpecModel(id='test_spec_3', display_name='Test Spec 3',
                                         description='Test Spec 3 Description', category_id=workflow_spec_category.id,
                                         display_order=3, standalone=False)
        session.add(spec_model_1)
        session.add(spec_model_2)
        session.add(spec_model_3)
        session.commit()

        self.app.delete('/v1.0/workflow-specification/test_spec_2', headers=self.logged_in_headers())

        test_order = 0
        specs = session.query(WorkflowSpecModel).\
            filter(WorkflowSpecModel.category_id == workflow_spec_category.id).\
            order_by(WorkflowSpecModel.display_order).\
            all()
        for test_spec in specs:
            self.assertEqual(test_order, test_spec.display_order)
            test_order += 1

    def test_get_standalone_workflow_specs(self):
        self.load_example_data()
        self.load_test_spec('random_fact')
        category = session.query(WorkflowSpecCategoryModel).first()
        ExampleDataLoader().create_spec('hello_world', 'Hello World', category_id=category.id,
                                        standalone=True, from_tests=True)
        rv = self.app.get('/v1.0/workflow-specification?standalone=true', headers=self.logged_in_headers())
        self.assertEqual(1, len(rv.json))

        ExampleDataLoader().create_spec('email_script', 'Email Script', category_id=category.id,
                                        standalone=True, from_tests=True)

        rv = self.app.get('/v1.0/workflow-specification?standalone=true', headers=self.logged_in_headers())
        self.assertEqual(2, len(rv.json))

    def test_get_workflow_from_workflow_spec(self):
        self.load_example_data()
        spec = ExampleDataLoader().create_spec('hello_world', 'Hello World', standalone=True, from_tests=True)
        rv = self.app.post(f'/v1.0/workflow-specification/{spec.id}', headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertEqual('hello_world', rv.json['workflow_spec_id'])
        self.assertEqual('Task_GetName', rv.json['next_task']['name'])

    def test_add_workflow_spec_category(self):
        self.load_example_data()
        count = session.query(WorkflowSpecCategoryModel).count()
        category = WorkflowSpecCategoryModel(
            id=count,
            display_name='Another Test Category',
            display_order=0
        )
        rv = self.app.post(f'/v1.0/workflow-specification-category',
                           headers=self.logged_in_headers(),
                           content_type="application/json",
                           data=json.dumps(WorkflowSpecCategoryModelSchema().dump(category))
                           )
        self.assert_success(rv)
        result = session.query(WorkflowSpecCategoryModel).filter(WorkflowSpecCategoryModel.id==count).first()
        self.assertEqual('Another Test Category', result.display_name)
        self.assertEqual(count, result.id)

    def test_update_workflow_spec_category(self):
        self.load_example_data()
        self.load_test_spec('random_fact')
        category = session.query(WorkflowSpecCategoryModel).first()
        display_name_before = category.display_name
        new_display_name = display_name_before + '_asdf'
        self.assertNotEqual(display_name_before, new_display_name)

        category.display_name = new_display_name

        rv = self.app.put(f'/v1.0/workflow-specification-category/{category.id}',
                          content_type="application/json",
                          headers=self.logged_in_headers(),
                          data=json.dumps(WorkflowSpecCategoryModelSchema().dump(category)))
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(new_display_name, json_data['display_name'])

    def test_delete_workflow_spec_category(self):
        self.load_example_data()
        category_model_1 = WorkflowSpecCategoryModel(
            id=1,
            display_name='Test Category 1',
            display_order=1
        )
        category_model_2 = WorkflowSpecCategoryModel(
            id=2,
            display_name='Test Category 2',
            display_order=2
        )
        category_model_3 = WorkflowSpecCategoryModel(
            id=3,
            display_name='Test Category 3',
            display_order=3
        )
        session.add(category_model_1)
        session.add(category_model_2)
        session.add(category_model_3)
        session.commit()

        rv = self.app.delete('/v1.0/workflow-specification-category/2', headers=self.logged_in_headers())
        self.assert_success(rv)
        test_order = 0
        categories = session.query(WorkflowSpecCategoryModel).order_by(WorkflowSpecCategoryModel.display_order).all()
        for test_category in categories:
            self.assertEqual(test_order, test_category.display_order)
            test_order += 1

    def test_add_library_with_category_id(self):
        self.load_example_data()
        self.load_test_spec('random_fact')
        category_id = session.query(WorkflowSpecCategoryModel).first().id
        spec = WorkflowSpecModel(id='test_spec', display_name='Test Spec',
                                 description='Library with a category id', category_id=category_id,
                                 standalone=False, library=True)
        rv = self.app.post('/v1.0/workflow-specification',
                           headers=self.logged_in_headers(),
                           content_type="application/json",
                           data=json.dumps(WorkflowSpecModelSchema().dump(spec)))
        self.assert_success(rv)
        # libraries don't get category_ids
        # so, the category_id should not get set
        self.assertIsNone(rv.json['category_id'])
