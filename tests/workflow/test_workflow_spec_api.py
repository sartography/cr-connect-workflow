import json
import os.path

from tests.base_test import BaseTest
from crc import session
from crc.models.workflow import WorkflowModel, WorkflowSpecInfoSchema, WorkflowSpecInfo, WorkflowSpecCategory, \
    WorkflowSpecCategorySchema
from crc.services.spec_file_service import SpecFileService

from example_data import ExampleDataLoader


class TestWorkflowSpec(BaseTest):

    def test_list_workflow_specifications(self):

        spec = self.load_test_spec('random_fact')
        rv = self.app.get('/v1.0/workflow-specification',
                          follow_redirects=True,
                          content_type="application/json",headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        specs = WorkflowSpecInfoSchema(many=True).load(json_data, partial=True)
        spec2 = specs[0]
        self.assertEqual(spec.id, spec2.id)
        self.assertEqual(spec.display_name, spec2.display_name)
        self.assertEqual(spec.description, spec2.description)

    def test_add_new_workflow_specification(self):
        self.assertEqual(0, len(self.workflow_spec_service.get_specs()))
        self.assertEqual(0, len(self.workflow_spec_service.get_categories()))
        cat = WorkflowSpecCategory(id="test_cat", display_name="Test Category", display_order=0, admin=False)
        self.workflow_spec_service.add_category(cat)
        spec = WorkflowSpecInfo(id='make_cookies', display_name='Cooooookies',
                                description='Om nom nom delicious cookies', category_id=cat.id,
                                standalone=False, is_review=False, is_master_spec=False, libraries=[], library=False,
                                primary_process_id='', primary_file_name='')
        rv = self.app.post('/v1.0/workflow-specification',
                           headers=self.logged_in_headers(),
                           content_type="application/json",
                           data=json.dumps(WorkflowSpecInfoSchema().dump(spec)))
        self.assert_success(rv)

        fs_spec = self.workflow_spec_service.get_spec('make_cookies')
        self.assertEqual(spec.display_name, fs_spec.display_name)
        self.assertEqual(0, fs_spec.display_order)
        self.assertEqual(1, len(self.workflow_spec_service.get_categories()))

    def test_get_workflow_specification(self):

        self.load_test_spec('random_fact')
        rv = self.app.get('/v1.0/workflow-specification/random_fact', headers=self.logged_in_headers())
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        api_spec = WorkflowSpecInfoSchema().load(json_data)

        fs_spec = self.workflow_spec_service.get_spec('random_fact')
        self.assertEqual(WorkflowSpecInfoSchema().dump(fs_spec), json_data)

    def test_update_workflow_specification(self):

        self.load_test_spec('random_fact')
        category_id = 'a_trap'
        category = WorkflowSpecCategory(id=category_id, display_name="It's a trap!", display_order=0, admin=False)
        self.workflow_spec_service.add_category(category)

        spec_before: WorkflowSpecInfo = self.workflow_spec_service.get_spec('random_fact')
        self.assertNotEqual(spec_before.category_id, category_id)

        spec_before.category_id = category_id
        rv = self.app.put('/v1.0/workflow-specification/random_fact',
                          content_type="application/json",
                          headers=self.logged_in_headers(),
                          data=json.dumps(WorkflowSpecInfoSchema().dump(spec_before)))
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        api_spec = WorkflowSpecInfoSchema().load(json_data)
        self.assertEqual(WorkflowSpecInfoSchema().dump(spec_before), json_data)


        spec_after: WorkflowSpecInfo = self.workflow_spec_service.get_spec('random_fact')
        self.assertIsNotNone(spec_after.category_id)
        self.assertIsNotNone(spec_after.category_id, category_id)

    def test_delete_workflow_specification(self):

        spec_id = 'random_fact'
        spec = self.load_test_spec(spec_id)
        workflow = self.create_workflow(spec_id)
        workflow_api = self.get_workflow_api(workflow)
        workflow_path = SpecFileService.workflow_path(spec)

        num_specs_before = len(self.workflow_spec_service.get_specs())
        self.assertEqual(num_specs_before, 1)
        num_files_before = len(SpecFileService.get_files(spec))
        num_workflows_before = session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id).count()
        self.assertGreater(num_files_before + num_workflows_before, 0)
        rv = self.app.delete('/v1.0/workflow-specification/' + spec_id, headers=self.logged_in_headers())
        self.assert_success(rv)

        num_specs_after = len(self.workflow_spec_service.get_specs())
        self.assertEqual(0, num_specs_after)

        # Make sure that all items in the database and file system are deleted as well.
        self.assertFalse(os.path.exists(workflow_path))
        num_workflows_after = session.query(WorkflowModel).filter_by(workflow_spec_id=spec_id).count()
        self.assertEqual(num_workflows_after, 1)

    def test_display_order_after_delete_spec(self):

        self.load_test_spec('random_fact')
        self.load_test_spec('decision_table')
        self.load_test_spec('email')


        all_specs = self.workflow_spec_service.get_categories()[0].specs
        for i in range(0, 3):
            self.assertEqual(i, all_specs[i].display_order)

        self.app.delete('/v1.0/workflow-specification/decision_table', headers=self.logged_in_headers())

        test_order = 0


        all_specs = self.workflow_spec_service.get_categories()[0].specs
        for i in range(0, 2):
            self.assertEqual(i, all_specs[i].display_order)

    def test_get_standalone_workflow_specs(self):

        self.load_test_spec('random_fact')

        category = self.workflow_spec_service.get_categories()[0]
        ExampleDataLoader().create_spec('hello_world', 'Hello World', category_id=category.id,
                                        standalone=True, from_tests=True)
        rv = self.app.get('/v1.0/workflow-specification?standalone=true', headers=self.logged_in_headers())
        self.assertEqual(1, len(rv.json))
        ExampleDataLoader().create_spec('email_script', 'Email Script', category_id=category.id,
                                        standalone=True, from_tests=True)
        rv = self.app.get('/v1.0/workflow-specification?standalone=true', headers=self.logged_in_headers())
        self.assertEqual(2, len(rv.json))

    def test_get_workflow_from_workflow_spec(self):

        spec = self.load_test_spec('hello_world')
        rv = self.app.post(f'/v1.0/workflow-specification/{spec.id}', headers=self.logged_in_headers())
        self.assert_success(rv)
        self.assertEqual('hello_world', rv.json['workflow_spec_id'])
        self.assertEqual('Task_GetName', rv.json['next_task']['name'])

    def test_add_workflow_spec_category(self):

        category = WorkflowSpecCategory(id="test", display_name='Another Test Category',display_order=0, admin=False)
        rv = self.app.post(f'/v1.0/workflow-specification-category',
                           headers=self.logged_in_headers(),
                           content_type="application/json",
                           data=json.dumps(WorkflowSpecCategorySchema().dump(category))
                           )
        self.assert_success(rv)

        result = WorkflowSpecCategorySchema().loads(rv.get_data(as_text=True))
        fs_category = self.workflow_spec_service.get_category('test')
        self.assertEqual('Another Test Category', result.display_name)
        self.assertEqual("test", result.id)

    def test_update_workflow_spec_category(self):

        self.load_test_spec('random_fact')

        category = self.workflow_spec_service.get_categories()[0]
        display_name_before = category.display_name
        new_display_name = display_name_before + '_asdf'
        self.assertNotEqual(display_name_before, new_display_name)
        category.display_name = new_display_name

        rv = self.app.put(f'/v1.0/workflow-specification-category/{category.id}',
                          content_type="application/json",
                          headers=self.logged_in_headers(),
                          data=json.dumps(WorkflowSpecCategorySchema().dump(category)))
        self.assert_success(rv)
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual(new_display_name, json_data['display_name'])

    def test_delete_workflow_spec_category(self):
        self.assure_category_name_exists('Test Category 1')
        self.assure_category_name_exists('Test Category 2')
        self.assure_category_name_exists('Test Category 3')
        rv = self.app.delete('/v1.0/workflow-specification-category/Test Category 2', headers=self.logged_in_headers())
        self.assert_success(rv)
        test_order = 0

        categories = self.workflow_spec_service.get_categories()
        self.assertEqual(2, len(categories))
        for test_category in categories:
            self.assertEqual(test_order, test_category.display_order)
            test_order += 1

    def test_add_library_with_category_id(self):

        self.load_test_spec('random_fact')

        category_id = self.workflow_spec_service.get_categories()[0].id
        spec = WorkflowSpecInfo(id='test_spec', display_name='Test Spec',
                                description='Library with a category id', category_id=category_id,
                                standalone=False, library=True, is_master_spec=False, is_review=False,
                                primary_process_id="", primary_file_name="", libraries=[])
        rv = self.app.post('/v1.0/workflow-specification',
                           headers=self.logged_in_headers(),
                           content_type="application/json",
                           data=json.dumps(WorkflowSpecInfoSchema().dump(spec)))
        self.assert_success(rv)
        # libraries don't get category_ids
        # so, the category_id should not get set
        self.assertEqual("", rv.json['category_id'])

