from tests.base_test import BaseTest


class TestLaneValidation(BaseTest):

    def test_lane_validation(self):
        spec_model = self.load_test_spec('lane')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)
