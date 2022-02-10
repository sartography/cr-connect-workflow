from tests.base_test import BaseTest

from crc.models.workflow import WorkflowSpecCategory
from crc.services.workflow_spec_service import WorkflowSpecService

import json


class TestWorkflowSpecCategoryReorder(BaseTest):

    @staticmethod
    def _load_test_categories():
        category_model_1 = WorkflowSpecCategory(
            id='test_category_1',
            display_name='Test Category 1',
            display_order=1
        )
        category_model_2 = WorkflowSpecCategory(
            id='test_category_2',
            display_name='Test Category 2',
            display_order=2
        )
        category_model_3 = WorkflowSpecCategory(
            id='test_category_3',
            display_name='Test Category 3',
            display_order=3
        )
        WorkflowSpecService().add_category(category_model_1)
        WorkflowSpecService().add_category(category_model_2)
        WorkflowSpecService().add_category(category_model_3)

    def test_initial_order(self):
        self._load_test_categories()
        categories = WorkflowSpecService().get_categories()
        categories.sort(key=lambda w: w.display_order)
        self.assertEqual('test_category_1', categories[0].id)
        self.assertEqual('test_category_2', categories[1].id)
        self.assertEqual('test_category_3', categories[2].id)

    def test_workflow_spec_category_reorder_up(self):
        self._load_test_categories()

        # Move category 2 up
        rv = self.app.put(f"/v1.0/workflow-specification-category/test_category_2/reorder?direction=up",
                          headers=self.logged_in_headers())
        self.assert_success(rv)
        # Make sure category 2 is in position 1 now
        self.assertEqual('test_category_2', rv.json[0]['id'])

        categories = WorkflowSpecService().get_categories()
        categories.sort(key=lambda w: w.display_order)
        self.assertEqual('test_category_2', categories[0].id)

    def test_workflow_spec_category_reorder_down(self):
        self._load_test_categories()

        # Move category 2 down
        rv = self.app.put(f"/v1.0/workflow-specification-category/test_category_2/reorder?direction=down",
                          headers=self.logged_in_headers())

        # Make sure category 2 is in position 3 now
        self.assertEqual('test_category_2', rv.json[2]['id'])

        categories = WorkflowSpecService().get_categories()
        categories.sort(key=lambda w: w.display_order)
        self.assertEqual('test_category_2', categories[2].id)

    def test_workflow_spec_category_reorder_bad_direction(self):
        self._load_test_categories()

        rv = self.app.put(f"/v1.0/workflow-specification-category/test_category_2/reorder?direction=asdf",
                          headers=self.logged_in_headers())
        self.assertEqual('bad_direction', rv.json['code'])
        self.assertEqual('The direction must be `up` or `down`.', rv.json['message'])

    def test_workflow_spec_category_reorder_bad_category_id(self):
        self._load_test_categories()

        rv = self.app.put(f"/v1.0/workflow-specification-category/test_category_10/reorder?direction=down",
                          headers=self.logged_in_headers())
        self.assertEqual('bad_category_id', rv.json['code'])
        self.assertEqual('The category id test_category_10 did not return a Workflow Spec Category. Make sure it is a valid ID.', rv.json['message'])

    def test_workflow_spec_category_down_too_far(self):
        self._load_test_categories()
        categories = WorkflowSpecService().get_categories()
        categories.sort(key=lambda w: w.display_order)

        # Try to move 3 down
        rv = self.app.put(f"/v1.0/workflow-specification-category/test_category_3/reorder?direction=down",
                          headers=self.logged_in_headers())
        # Make sure we don't get an error
        self.assert_success(rv)

        # Make sure we get the original list back.
        new_categories = WorkflowSpecService().get_categories()
        new_categories.sort(key=lambda w: w.display_order)

        self.assertEqual(categories[0].id, new_categories[0].id)
        self.assertEqual(categories[1].id, new_categories[1].id)
        self.assertEqual(categories[2].id, new_categories[2].id)

    def test_workflow_spec_category_up_too_far(self):

        self._load_test_categories()

        categories = WorkflowSpecService().get_categories()
        categories.sort(key=lambda w: w.display_order)

        # Try to move 1 up
        rv = self.app.put(f"/v1.0/workflow-specification-category/test_category_1/reorder?direction=up",
                          headers=self.logged_in_headers())
        # Make sure we don't get an error
        self.assert_success(rv)

        # Make sure we get the original list back.
        new_categories = WorkflowSpecService().get_categories()
        new_categories.sort(key=lambda w: w.display_order)

        self.assertEqual(categories[0].id, new_categories[0].id)
        self.assertEqual(categories[1].id, new_categories[1].id)
        self.assertEqual(categories[2].id, new_categories[2].id)

    def test_workflow_spec_category_bad_order(self):

        self._load_test_categories()
        workflow_spec_service = WorkflowSpecService()

        categories = workflow_spec_service.get_categories()
        categories.sort(key=lambda w: w.display_order)
        # Create bad display_orders
        # 3 of them have 1 as their display_order
        wf_spec_category = categories[0]
        wf_spec_category.display_order = 1
        workflow_spec_service.update_category(wf_spec_category)

        wf_spec_category = categories[1]
        wf_spec_category.display_order = 1
        workflow_spec_service.update_category(wf_spec_category)

        wf_spec_category = categories[2]
        wf_spec_category.display_order = 1
        workflow_spec_service.update_category(wf_spec_category)

        new_categories = WorkflowSpecService().get_categories()
        new_categories.sort(key=lambda w: w.display_order)

        # Confirm the bad display_orders (They all have 1 as display_order)
        self.assertEqual('Test Category 3', new_categories[0].display_name)
        self.assertEqual(1, new_categories[0].display_order)
        self.assertEqual('Test Category 2', new_categories[1].display_name)
        self.assertEqual(1, new_categories[1].display_order)
        self.assertEqual('Test Category 1', new_categories[2].display_name)
        self.assertEqual(1, new_categories[2].display_order)

        # Reorder 1 up
        # This should cause a cleanup of the display_orders
        rv = self.app.put(f"/v1.0/workflow-specification-category/test_category_1/reorder?direction=up",
                          headers=self.logged_in_headers())
        json_data = json.loads(rv.get_data(as_text=True))
        self.assertEqual('Test Category 3', json_data[0]['display_name'])
        self.assertEqual(0, json_data[0]['display_order'])
        self.assertEqual('Test Category 1', json_data[1]['display_name'])
        self.assertEqual(1, json_data[1]['display_order'])
        self.assertEqual('Test Category 2', json_data[2]['display_name'])
        self.assertEqual(2, json_data[2]['display_order'])
