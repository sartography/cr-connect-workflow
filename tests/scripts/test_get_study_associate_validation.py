from tests.base_test import BaseTest
from crc import app


class TestGetStudyAssociateValidation(BaseTest):

    def test_get_study_associate_validation(self):

        self.load_example_data()
        workflow = self.create_workflow('get_study_associate')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % workflow.workflow_spec_id,
                          headers=self.logged_in_headers())
        self.assertEqual(0, len(rv.json))
