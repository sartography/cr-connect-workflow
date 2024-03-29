from tests.base_test import BaseTest

from crc import session
from crc.models.study import StudyModel
from crc.services.study_service import StudyService
from crc.services.workflow_spec_service import WorkflowSpecService


class TestStudyStatusMessage(BaseTest):

    """The workflow runs with a workflow_meta.name of `random_fact`
       Add an entry to `status` dictionary with a key of `random_fact`"""

    def run_update_status(self, status):
        # shared code
        self.load_test_spec('random_fact')
        self.create_workflow('random_fact')
        study_model = session.query(StudyModel).first()
        spec_service = WorkflowSpecService()
        workflow_metas = StudyService._get_workflow_metas(study_model.id, spec_service.get_categories()[0])
        warnings = StudyService.get_study_warnings(workflow_metas, status)
        return workflow_metas, warnings

    def test_study_status_message_bad_name(self):
        # we don't have an entry for you in the status dictionary
        status = {'bad_name': {'status': 'hidden', 'message': 'This is my status message!'}}
        workflow_metas, warnings = self.run_update_status(status)

        self.assertEqual(2, len(warnings))
        self.assertEqual('missing_status', warnings[0].code)
        self.assertEqual('No status information provided about workflow random_fact', warnings[0].message)
        self.assertEqual('unmatched_status', warnings[1].code)
        self.assertEqual('The master workflow provided a status for \'bad_name\' a workflow that doesn\'t'
                         ' seem to exist.', warnings[1].message)

    def test_study_status_message_not_dict(self):
        # your entry in the status dictionary is not a dictionary
        status = {'random_fact':  'This is my status message!'}
        workflow_metas, warnings = self.run_update_status(status)

        self.assertEqual(1, len(warnings))
        self.assertEqual('invalid_status', warnings[0].code)
        self.assertEqual('Status must be a dictionary with "status" and "message" keys. Name is random_fact. Status is This is my status message!',
                         warnings[0].message)

    def test_study_status_message_bad_state(self):
        # you have an invalid state
        # I.e., not in (hidden,disabled,required,optional)
        status = {'random_fact': {'status': 'hide', 'message': 'This is my status message!'}}
        workflow_metas, warnings = self.run_update_status(status)
        self.assertEqual(1, len(warnings))
        self.assertEqual('invalid_state', warnings[0].code)
        self.assertEqual('Workflow \'random_fact\' can not be set to \'hide\', should be one of hidden,disabled,required,optional,locked',
                         warnings[0].message)
