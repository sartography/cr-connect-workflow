from tests.base_test import BaseTest

from crc import session
from crc.models.workflow import WorkflowSpecInfo, WorkflowSpecInfoSchema
from crc.services.workflow_spec_service import WorkflowSpecService

import json


class TestWorkflowSpecReorder(BaseTest):

    def _load_sample_workflow_specs(self):
        self.load_test_spec('random_fact')
        self.assure_category_exists('test_category')
        spec_model_1 = WorkflowSpecInfo(id='test_spec_1',
                                        display_name='Test Spec 1',
                                        description='Test Spec 1 Description',
                                        category_id='test_category')
        rv_1 = self.app.post('/v1.0/workflow-specification',
                             headers=self.logged_in_headers(),
                             content_type="application/json",
                             data=json.dumps(WorkflowSpecInfoSchema().dump(spec_model_1)))
        spec_model_2 = WorkflowSpecInfo(id='test_spec_2',
                                        display_name='Test Spec 2',
                                        description='Test Spec 2 Description',
                                        category_id='test_category')
        rv_2 = self.app.post('/v1.0/workflow-specification',
                             headers=self.logged_in_headers(),
                             content_type="application/json",
                             data=json.dumps(WorkflowSpecInfoSchema().dump(spec_model_2)))
        spec_model_3 = WorkflowSpecInfo(id='test_spec_3',
                                        display_name='Test Spec 3',
                                        description='Test Spec 3 Description',
                                        category_id='test_category')
        rv_3 = self.app.post('/v1.0/workflow-specification',
                             headers=self.logged_in_headers(),
                             content_type="application/json",
                             data=json.dumps(WorkflowSpecInfoSchema().dump(spec_model_3)))
        return rv_1, rv_2, rv_3

    def test_load_sample_workflow_specs(self):
        rv_1, rv_2, rv_3 = self._load_sample_workflow_specs()
        self.assertEqual(1, rv_1.json['display_order'])
        self.assertEqual('test_spec_1', rv_1.json['id'])
        self.assertEqual(2, rv_2.json['display_order'])
        self.assertEqual('test_spec_2', rv_2.json['id'])
        self.assertEqual(3, rv_3.json['display_order'])
        self.assertEqual('test_spec_3', rv_3.json['id'])

    def test_workflow_spec_reorder_bad_direction(self):
        self._load_sample_workflow_specs()
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_2/reorder?direction=asdf",
                          headers=self.logged_in_headers())
        self.assertEqual('400 BAD REQUEST', rv.status)
        self.assertEqual("The direction must be `up` or `down`.", rv.json['message'])

    def test_workflow_spec_reorder_bad_spec_id(self):
        self.load_example_data()
        self._load_sample_workflow_specs()
        rv = self.app.put(f"/v1.0/workflow-specification/10/reorder?direction=up",
                          headers=self.logged_in_headers())
        self.assertEqual('bad_spec_id', rv.json['code'])
        self.assertEqual('The spec_id 10 did not return a specification. Please check that it is valid.', rv.json['message'])

    def test_workflow_spec_reorder_up(self):
        rv_1, rv_2, rv_3 = self._load_sample_workflow_specs()
        category_id = rv_1.json['category_id']
        # Get the current order
        specs = WorkflowSpecService().get_specs()
        specs.sort(key=lambda w: w.display_order)

        self.assertEqual('test_spec_2', specs[2].id)

        # Move test_spec_2 up
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_2/reorder?direction=up",
                          headers=self.logged_in_headers())

        # rv json contains the newly order list of specs
        self.assertEqual(1, rv.json[1]['display_order'])
        self.assertEqual('test_spec_2', rv.json[1]['id'])

        # Get the new order
        new_specs = WorkflowSpecService().get_specs()
        new_specs.sort(key=lambda w: w.display_order)

        self.assertEqual('test_spec_2', new_specs[1].id)
        print('test_workflow_spec_reorder_up')

    def test_workflow_spec_reorder_down(self):
        rv_1, rv_2, rv_3 = self._load_sample_workflow_specs()
        category_id = rv_1.json['category_id']

        # Check what order is in the DB
        specs = WorkflowSpecService().get_specs()
        specs.sort(key=lambda w: w.display_order)
        self.assertEqual('test_spec_2', specs[2].id)

        # Move test_spec_2 down
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_2/reorder?direction=down",
                          headers=self.logged_in_headers())

        # rv json contains the newly order list of specs
        self.assertEqual('test_spec_2', rv.json[3]['id'])
        self.assertEqual(3, rv.json[3]['display_order'])

        # Check what new order is in the DB
        new_specs = WorkflowSpecService().get_specs()
        new_specs.sort(key=lambda w: w.display_order)

        self.assertEqual('test_spec_2', new_specs[3].id)

    def test_workflow_spec_reorder_down_bad(self):
        rv_1, rv_2, rv_3 = self._load_sample_workflow_specs()
        category_id = rv_1.json['category_id']

        specs = WorkflowSpecService().get_specs()
        specs.sort(key=lambda w: w.display_order)

        # Try to move test_spec_3 down
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_3/reorder?direction=down",
                          headers=self.logged_in_headers())
        # Make sure we don't get an error
        self.assert_success(rv)

        # Make sure we get the original list back.
        new_specs = WorkflowSpecService().get_specs()
        new_specs.sort(key=lambda w: w.display_order)

        self.assertEqual(specs[0].id, new_specs[0].id)
        self.assertEqual(specs[1].id, new_specs[1].id)
        self.assertEqual(specs[2].id, new_specs[2].id)
        self.assertEqual(specs[3].id, new_specs[3].id)

    def test_workflow_spec_reorder_bad_order(self):
        rv_1, rv_2, rv_3 = self._load_sample_workflow_specs()
        category_id = rv_1.json['category_id']

        specs = WorkflowSpecService().get_specs()
        specs.sort(key=lambda w: w.display_order)

        # Set bad display_orders
        spec_model = specs[0]
        spec_model.display_order = 1
        WorkflowSpecService().update_spec(spec_model)
        # session.add(spec_model)
        spec_model = specs[1]
        spec_model.display_order = 1
        WorkflowSpecService().update_spec(spec_model)
        # session.add(spec_model)
        spec_model = specs[2]
        spec_model.display_order = 1
        WorkflowSpecService().update_spec(spec_model)
        # session.add(spec_model)
        # session.commit()

        bad_specs = WorkflowSpecService().get_specs()
        bad_specs.sort(key=lambda w: w.display_order)

        self.assertEqual(1, bad_specs[0].display_order)
        self.assertEqual('test_spec_2', bad_specs[0].id)
        self.assertEqual(1, bad_specs[1].display_order)
        self.assertEqual('random_fact', bad_specs[1].id)
        self.assertEqual(1, bad_specs[2].display_order)
        self.assertEqual('test_spec_1', bad_specs[2].id)
        self.assertEqual(3, bad_specs[3].display_order)
        self.assertEqual('test_spec_3', bad_specs[3].id)

        # Move test_spec_2 up
        # This should cause a cleanup of the bad display_order numbers
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_2/reorder?direction=up",
                          headers=self.logged_in_headers())

        # After moving 2 up, the order should be
        # test_spec_1, test_spec_2, random_fact, test_spec_3
        # Make sure we have good display_order numbers too
        self.assertEqual('test_spec_2', rv.json[0]['id'])
        self.assertEqual(0, rv.json[0]['display_order'])
        self.assertEqual('random_fact', rv.json[1]['id'])
        self.assertEqual(1, rv.json[1]['display_order'])
        self.assertEqual('test_spec_1', rv.json[2]['id'])
        self.assertEqual(2, rv.json[2]['display_order'])
        self.assertEqual('test_spec_3', rv.json[3]['id'])
        self.assertEqual(3, rv.json[3]['display_order'])
