from tests.base_test import BaseTest

from crc import session
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowSpecCategoryModel

import json


class TestWorkflowSpecReorder(BaseTest):

    def _load_sample_workflow_specs(self):
        workflow_spec_category = session.query(WorkflowSpecCategoryModel).first()
        spec_model_1 = WorkflowSpecModel(id='test_spec_1', display_name='Test Spec 1',
                                         description='Test Spec 1 Description', category_id=workflow_spec_category.id,
                                         standalone=False)
        rv_1 = self.app.post('/v1.0/workflow-specification',
                             headers=self.logged_in_headers(),
                             content_type="application/json",
                             data=json.dumps(WorkflowSpecModelSchema().dump(spec_model_1)))
        spec_model_2 = WorkflowSpecModel(id='test_spec_2', display_name='Test Spec 2',
                                         description='Test Spec 2 Description', category_id=workflow_spec_category.id,
                                         standalone=False)
        rv_2 = self.app.post('/v1.0/workflow-specification',
                             headers=self.logged_in_headers(),
                             content_type="application/json",
                             data=json.dumps(WorkflowSpecModelSchema().dump(spec_model_2)))
        spec_model_3 = WorkflowSpecModel(id='test_spec_3', display_name='Test Spec 3',
                                         description='Test Spec 3 Description', category_id=workflow_spec_category.id,
                                         standalone=False)
        rv_3 = self.app.post('/v1.0/workflow-specification',
                             headers=self.logged_in_headers(),
                             content_type="application/json",
                             data=json.dumps(WorkflowSpecModelSchema().dump(spec_model_3)))
        return rv_1, rv_2, rv_3

    def test_load_sample_workflow_specs(self):
        self.load_example_data()
        rv_1, rv_2, rv_3 = self._load_sample_workflow_specs()
        self.assertEqual(1, rv_1.json['display_order'])
        self.assertEqual('test_spec_1', rv_1.json['id'])
        self.assertEqual(2, rv_2.json['display_order'])
        self.assertEqual('test_spec_2', rv_2.json['id'])
        self.assertEqual(3, rv_3.json['display_order'])
        self.assertEqual('test_spec_3', rv_3.json['id'])

    def test_workflow_spec_reorder_bad_direction(self):
        self.load_example_data()
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
        self.load_example_data()
        self._load_sample_workflow_specs()

        # Check what order is in the DB
        ordered = session.query(WorkflowSpecModel).\
            filter(WorkflowSpecModel.category_id == 0).\
            order_by(WorkflowSpecModel.display_order).\
            all()
        self.assertEqual('test_spec_2', ordered[2].id)

        # Move test_spec_2 up
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_2/reorder?direction=up",
                          headers=self.logged_in_headers())

        # rv json contains the newly order list of specs
        self.assertEqual(1, rv.json[1]['display_order'])
        self.assertEqual('test_spec_2', rv.json[1]['id'])

        # Check what new order is in the DB
        reordered = session.query(WorkflowSpecModel).\
            filter(WorkflowSpecModel.category_id == 0).\
            order_by(WorkflowSpecModel.display_order).\
            all()
        self.assertEqual('test_spec_2', reordered[1].id)
        print('test_workflow_spec_reorder_up')

    def test_workflow_spec_reorder_down(self):
        self.load_example_data()
        self._load_sample_workflow_specs()

        # Check what order is in the DB
        ordered = session.query(WorkflowSpecModel).\
            filter(WorkflowSpecModel.category_id == 0).\
            order_by(WorkflowSpecModel.display_order).\
            all()
        self.assertEqual('test_spec_2', ordered[2].id)

        # Move test_spec_2 down
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_2/reorder?direction=down",
                          headers=self.logged_in_headers())

        # rv json contains the newly order list of specs
        self.assertEqual('test_spec_2', rv.json[3]['id'])
        self.assertEqual(3, rv.json[3]['display_order'])

        # Check what new order is in the DB
        reordered = session.query(WorkflowSpecModel).\
            filter(WorkflowSpecModel.category_id == 0).\
            order_by(WorkflowSpecModel.display_order).\
            all()
        self.assertEqual('test_spec_2', reordered[3].id)

    def test_workflow_spec_reorder_down_bad(self):
        self.load_example_data()
        self._load_sample_workflow_specs()

        ordered = session.query(WorkflowSpecModel).\
            filter(WorkflowSpecModel.category_id == 0).\
            order_by(WorkflowSpecModel.display_order).\
            all()

        # Try to move test_spec_3 down
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_3/reorder?direction=down",
                          headers=self.logged_in_headers())
        # Make sure we don't get an error
        self.assert_success(rv)

        # Make sure we get the original list back.
        reordered = session.query(WorkflowSpecModel).\
            filter(WorkflowSpecModel.category_id == 0).\
            order_by(WorkflowSpecModel.display_order).\
            all()
        self.assertEqual(ordered, reordered)

    def test_workflow_spec_reorder_bad_order(self):
        self.load_example_data()
        self._load_sample_workflow_specs()
        ordered = session.query(WorkflowSpecModel).\
            filter(WorkflowSpecModel.category_id == 0).\
            order_by(WorkflowSpecModel.display_order).\
            all()

        # Set bad display_orders
        spec_model = ordered[0]
        spec_model.display_order = 1
        session.add(spec_model)
        spec_model = ordered[1]
        spec_model.display_order = 1
        session.add(spec_model)
        spec_model = ordered[2]
        spec_model.display_order = 1
        session.add(spec_model)
        session.commit()

        bad_orders = session.query(WorkflowSpecModel).\
            filter(WorkflowSpecModel.category_id == 0).\
            order_by(WorkflowSpecModel.display_order).\
            all()
        # Not sure how Postgres chooses an order
        # when we have multiple specs with display_order == 1
        # but it is
        # test_spec_1, random_fact, test_spec_2, test_spec_3
        self.assertEqual(1, bad_orders[0].display_order)
        self.assertEqual('test_spec_1', bad_orders[0].id)
        self.assertEqual(1, bad_orders[1].display_order)
        self.assertEqual('random_fact', bad_orders[1].id)
        self.assertEqual(1, bad_orders[2].display_order)
        self.assertEqual('test_spec_2', bad_orders[2].id)
        self.assertEqual(3, bad_orders[3].display_order)
        self.assertEqual('test_spec_3', bad_orders[3].id)

        # Move test_spec_2 up
        # This should cause a cleanup of the bad display_order numbers
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_2/reorder?direction=up",
                          headers=self.logged_in_headers())

        # After moving 2 up, the order should be
        # test_spec_1, test_spec_2, random_fact, test_spec_3
        # Make sure we have good display_order numbers too
        self.assertEqual('test_spec_1', rv.json[0]['id'])
        self.assertEqual(0, rv.json[0]['display_order'])
        self.assertEqual('test_spec_2', rv.json[1]['id'])
        self.assertEqual(1, rv.json[1]['display_order'])
        self.assertEqual('random_fact', rv.json[2]['id'])
        self.assertEqual(2, rv.json[2]['display_order'])
        self.assertEqual('test_spec_3', rv.json[3]['id'])
        self.assertEqual(3, rv.json[3]['display_order'])
