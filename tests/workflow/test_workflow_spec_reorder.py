from tests.base_test import BaseTest

from crc import session
from crc.models.workflow import WorkflowSpecModel, WorkflowSpecModelSchema, WorkflowSpecCategoryModel

import json


class TestWorkflowSpecReorder(BaseTest):

    def _load_sample_workflow_specs(self):
        self.load_example_data()
        workflow_spec_category = session.query(WorkflowSpecCategoryModel).first()
        spec_model_1 = WorkflowSpecModel(id='test_spec_1', name='test_spec_1', display_name='Test Spec 1',
                                         description='Test Spec 1 Description', category_id=workflow_spec_category.id,
                                         standalone=False)
        rv_1 = self.app.post('/v1.0/workflow-specification',
                             headers=self.logged_in_headers(),
                             content_type="application/json",
                             data=json.dumps(WorkflowSpecModelSchema().dump(spec_model_1)))
        spec_model_2 = WorkflowSpecModel(id='test_spec_2', name='test_spec_2', display_name='Test Spec 2',
                                         description='Test Spec 2 Description', category_id=workflow_spec_category.id,
                                         standalone=False)
        rv_2 = self.app.post('/v1.0/workflow-specification',
                             headers=self.logged_in_headers(),
                             content_type="application/json",
                             data=json.dumps(WorkflowSpecModelSchema().dump(spec_model_2)))
        spec_model_3 = WorkflowSpecModel(id='test_spec_3', name='test_spec_3', display_name='Test Spec 3',
                                         description='Test Spec 3 Description', category_id=workflow_spec_category.id,
                                         standalone=False)
        rv_3 = self.app.post('/v1.0/workflow-specification',
                             headers=self.logged_in_headers(),
                             content_type="application/json",
                             data=json.dumps(WorkflowSpecModelSchema().dump(spec_model_3)))
        return rv_1, rv_2, rv_3

    def test_load_sample_workflow_specs(self):
        rv_1, rv_2, rv_3 = self._load_sample_workflow_specs()
        self.assertEqual(1, rv_1.json['display_order'])
        self.assertEqual('test_spec_1', rv_1.json['name'])
        self.assertEqual(2, rv_2.json['display_order'])
        self.assertEqual('test_spec_2', rv_2.json['name'])
        self.assertEqual(3, rv_3.json['display_order'])
        self.assertEqual('test_spec_3', rv_3.json['name'])

    def test_workflow_spec_reorder_bad_direction(self):
        self._load_sample_workflow_specs()
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_2/reorder?direction=asdf",
                          headers=self.logged_in_headers())
        self.assertEqual('400 BAD REQUEST', rv.status)
        self.assertEqual("The direction must be `up` or `down`.", rv.json['message'])

    def test_workflow_spec_reorder_bad_spec_id(self):
        self._load_sample_workflow_specs()
        rv = self.app.put(f"/v1.0/workflow-specification/10/reorder?direction=up",
                          headers=self.logged_in_headers())
        self.assertEqual('bad_spec_id', rv.json['code'])
        self.assertEqual('The spec_id 10 did not return a specification. Please check that it is valid.', rv.json['message'])

    def test_workflow_spec_reorder_up(self):
        self._load_sample_workflow_specs()

        # Check what order is in the DB
        ordered = session.query(WorkflowSpecModel).order_by(WorkflowSpecModel.display_order).all()
        self.assertEqual('test_spec_2', ordered[2].id)

        # Move test_spec_2 up
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_2/reorder?direction=up",
                          headers=self.logged_in_headers())

        # rv json contains the newly order list of specs
        self.assertEqual(1, rv.json[1]['display_order'])
        self.assertEqual('test_spec_2', rv.json[1]['id'])

        # Check what new order is in the DB
        reordered = session.query(WorkflowSpecModel).order_by(WorkflowSpecModel.display_order).all()
        self.assertEqual('test_spec_2', reordered[1].id)
        print('test_workflow_spec_reorder_up')

    def test_workflow_spec_reorder_down(self):
        self._load_sample_workflow_specs()

        # Check what order is in the DB
        ordered = session.query(WorkflowSpecModel).order_by(WorkflowSpecModel.display_order).all()
        self.assertEqual('test_spec_2', ordered[2].id)

        # Move test_spec_2 down
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_2/reorder?direction=down",
                          headers=self.logged_in_headers())

        # rv json contains the newly order list of specs
        self.assertEqual('test_spec_2', rv.json[3]['id'])
        self.assertEqual(3, rv.json[3]['display_order'])

        # Check what new order is in the DB
        reordered = session.query(WorkflowSpecModel).order_by(WorkflowSpecModel.display_order).all()
        self.assertEqual('test_spec_2', reordered[3].id)

    def test_workflow_spec_reorder_down_bad(self):
        self._load_sample_workflow_specs()

        ordered = session.query(WorkflowSpecModel).order_by(WorkflowSpecModel.display_order).all()

        # Try to move test_spec_3 down
        rv = self.app.put(f"/v1.0/workflow-specification/test_spec_3/reorder?direction=down",
                          headers=self.logged_in_headers())
        # Make sure we don't get an error
        self.assert_success(rv)

        # Make sure we get the original list back.
        reordered = session.query(WorkflowSpecModel).order_by(WorkflowSpecModel.display_order).all()
        self.assertEqual(ordered, reordered)
