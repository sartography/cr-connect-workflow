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

    def test_workflow_spec_reorder_no_direction(self):
        rv_1, rv_2, rv_3 = self._load_sample_workflow_specs()
        rv = self.app.put(f"/v1.0/workflow-specification/{rv_2.json['id']}/reorder?direction=asdf",
                          headers=self.logged_in_headers())
        self.assertEqual('400 BAD REQUEST', rv.status)
        self.assertEqual("The direction must be `up` or `down`.", rv.json['message'])

        print('test_workflow_spec_reorder_no_direction')

    def test_workflow_spec_reorder_up(self):
        rv_1, rv_2, rv_3 = self._load_sample_workflow_specs()

        self.assertEqual(1, rv_1.json['display_order'])
        self.assertEqual(2, rv_2.json['display_order'])
        self.assertEqual(3, rv_3.json['display_order'])

        rv = self.app.put(f"/v1.0/workflow-specification/{rv_2.json['id']}/reorder?direction=up",
                          headers=self.logged_in_headers())
        changed = session.query(WorkflowSpecModel).filter(WorkflowSpecModel.id == 'test_spec_2').first()
        self.assertEqual(1, changed.display_order)

        print('test_workflow_spec_reorder')
