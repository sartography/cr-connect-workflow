from tests.base_test import BaseTest

from crc import session
from crc.api.common import ApiError
from crc.models.workflow import WorkflowSpecCategoryModel

import json


class TestWorkflowSpecCategoryReorder(BaseTest):

    @staticmethod
    def _load_test_categories():
        category_model_1 = WorkflowSpecCategoryModel(
            id=1,
            name='test_category_1',
            display_name='Test Category 1',
            display_order=1
        )
        category_model_2 = WorkflowSpecCategoryModel(
            id=2,
            name='test_category_2',
            display_name='Test Category 2',
            display_order=2
        )
        category_model_3 = WorkflowSpecCategoryModel(
            id=3,
            name='test_category_3',
            display_name='Test Category 3',
            display_order=3
        )
        session.add(category_model_1)
        session.add(category_model_2)
        session.add(category_model_3)
        session.commit()

    def test_initial_order(self):
        self.load_example_data()
        self._load_test_categories()
        initial_order = session.query(WorkflowSpecCategoryModel).order_by(WorkflowSpecCategoryModel.display_order).all()
        self.assertEqual(0, initial_order[0].id)
        self.assertEqual(1, initial_order[1].id)
        self.assertEqual(2, initial_order[2].id)
        self.assertEqual(3, initial_order[3].id)

    def test_workflow_spec_category_reorder_up(self):
        self.load_example_data()
        self._load_test_categories()

        # Move category 2 up
        rv = self.app.put(f"/v1.0/workflow-specification-category/2/reorder?direction=up",
                          headers=self.logged_in_headers())

        # Make sure category 2 is in position 1 now
        self.assertEqual(2, rv.json[1]['id'])

        ordered = session.query(WorkflowSpecCategoryModel).\
            order_by(WorkflowSpecCategoryModel.display_order).all()
        self.assertEqual(2, ordered[1].id)

    def test_workflow_spec_category_reorder_down(self):
        self.load_example_data()
        self._load_test_categories()

        # Move category 2 down
        rv = self.app.put(f"/v1.0/workflow-specification-category/2/reorder?direction=down",
                          headers=self.logged_in_headers())

        # Make sure category 2 is in position 3 now
        self.assertEqual(2, rv.json[3]['id'])

        ordered = session.query(WorkflowSpecCategoryModel). \
            order_by(WorkflowSpecCategoryModel.display_order).all()
        self.assertEqual(2, ordered[3].id)

    def test_workflow_spec_category_reorder_bad_direction(self):
        self.load_example_data()
        self._load_test_categories()

        rv = self.app.put(f"/v1.0/workflow-specification-category/2/reorder?direction=asdf",
                          headers=self.logged_in_headers())
        self.assertEqual('bad_direction', rv.json['code'])
        self.assertEqual('The direction must be `up` or `down`.', rv.json['message'])

    def test_workflow_spec_category_reorder_bad_category_id(self):
        self.load_example_data()
        self._load_test_categories()

        # with self.assertRaises(ApiError):
        rv = self.app.put(f"/v1.0/workflow-specification-category/10/reorder?direction=down",
                          headers=self.logged_in_headers())
        self.assertEqual('bad_category_id', rv.json['code'])
        self.assertEqual('The category id 10 did not return a Workflow Spec Category. Make sure it is a valid ID.', rv.json['message'])

    def test_workflow_spec_category_down_too_far(self):
        self.load_example_data()
        self._load_test_categories()
        ordered = session.query(WorkflowSpecCategoryModel).order_by(WorkflowSpecCategoryModel.display_order).all()

        # Try to move 3 down
        rv = self.app.put(f"/v1.0/workflow-specification-category/3/reorder?direction=down",
                          headers=self.logged_in_headers())
        # Make sure we don't get an error
        self.assert_success(rv)

        # Make sure we get the original list back.
        reordered = session.query(WorkflowSpecCategoryModel).order_by(WorkflowSpecCategoryModel.display_order).all()
        self.assertEqual(ordered, reordered)

    def test_workflow_spec_category_up_too_far(self):
        self.load_example_data()
        self._load_test_categories()
        ordered = session.query(WorkflowSpecCategoryModel).order_by(WorkflowSpecCategoryModel.display_order).all()

        # Try to move 0 up
        rv = self.app.put(f"/v1.0/workflow-specification-category/0/reorder?direction=up",
                          headers=self.logged_in_headers())
        # Make sure we don't get an error
        self.assert_success(rv)

        # Make sure we get the original list back.
        reordered = session.query(WorkflowSpecCategoryModel).order_by(WorkflowSpecCategoryModel.display_order).all()
        self.assertEqual(ordered, reordered)

    def test_workflow_spec_category_bad_order(self):
        self.load_example_data()
        self._load_test_categories()
        ordered = session.query(WorkflowSpecCategoryModel).order_by(WorkflowSpecCategoryModel.display_order).all()
        # Create bad display_orders
        # 3 of them have 1 as their display_order
        wf_spec_category_model = ordered[0]
        wf_spec_category_model.display_order = 1
        session.add(wf_spec_category_model)
        wf_spec_category_model = ordered[1]
        wf_spec_category_model.display_order = 1
        session.add(wf_spec_category_model)
        wf_spec_category_model = ordered[2]
        wf_spec_category_model.display_order = 1
        session.add(wf_spec_category_model)
        session.commit()

        bad_ordered = session.query(WorkflowSpecCategoryModel).order_by(WorkflowSpecCategoryModel.display_order).all()
        # Confirm the bad display_orders
        self.assertEqual('Test Category 1', bad_ordered[0].display_name)
        self.assertEqual(1, bad_ordered[0].display_order)
        self.assertEqual('Test Category', bad_ordered[1].display_name)
        self.assertEqual(1, bad_ordered[1].display_order)
        self.assertEqual('Test Category 2', bad_ordered[2].display_name)
        self.assertEqual(1, bad_ordered[2].display_order)
        self.assertEqual('Test Category 3', bad_ordered[3].display_name)
        self.assertEqual(3, bad_ordered[3].display_order)

        # Reorder 2 up
        # This should cause a cleanup of the display_orders
        # I don't know how Postgres/SQLAlchemy determine the order when
        # multiple categories have the same display_order
        # But, it ends up
        # Test Category 1, Test Category, Test Category 2, Test Category 3
        # So, after moving 2 up, we should end up with
        # Test Category 1, Test Category 2, Test Category, Test Category 3
        rv = self.app.put(f"/v1.0/workflow-specification-category/2/reorder?direction=up",
                          headers=self.logged_in_headers())
        self.assertEqual('Test Category 1', rv.json[0]['display_name'])
        self.assertEqual(0, rv.json[0]['display_order'])
        self.assertEqual('Test Category 2', rv.json[1]['display_name'])
        self.assertEqual(1, rv.json[1]['display_order'])
        self.assertEqual('Test Category', rv.json[2]['display_name'])
        self.assertEqual(2, rv.json[2]['display_order'])
        self.assertEqual('Test Category 3', rv.json[3]['display_name'])
        self.assertEqual(3, rv.json[3]['display_order'])
