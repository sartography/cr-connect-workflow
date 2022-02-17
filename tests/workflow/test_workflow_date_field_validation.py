from tests.base_test import BaseTest


class TestDateValidation(BaseTest):

    def test_date_validation(self):

        """We were not instantiating date fields correctly during validation.
        This is a simple test to make sure we seed an actual date in date fields instead of a random string."""
        spec_model = self.load_test_spec('date_validation')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)
