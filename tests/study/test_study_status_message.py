from tests.base_test import BaseTest
from crc import db, session
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowState
from crc.services.study_service import StudyService


class TestStudyStatusMessage(BaseTest):

    """The workflow runs with a workflow_meta.name of `random_fact`
       Add an entry to `status` dictionary with a key of `random_fact`"""

    def run_update_status(self, status):
        # shared code
        self.load_example_data()
        study_model = session.query(StudyModel).first()
        workflow_metas = StudyService._get_workflow_metas(study_model.id)
        warnings = StudyService._update_status_of_workflow_meta(workflow_metas, status)
        return workflow_metas, warnings

    def test_study_status_message(self):
        # these are the passing tests
        # we loop through each Workflow state
        # (hidden,disabled,required,optional)
        for state in WorkflowState:
            # use state.value to set status['status'],
            status = {'random_fact':
                      {'status': state.value,
                       'message': 'This is my status message!'}}

            # call run_update_status(),
            workflow_metas, warnings = self.run_update_status(status)

            # and assert the values of workflow_metas[0].state and workflow_metas[0].state_message
            self.assertEqual(0, len(warnings))
            self.assertEqual(state, workflow_metas[0].state)
            self.assertEqual('This is my status message!', workflow_metas[0].state_message)

    def test_study_status_message_bad_name(self):
        # we don't have an entry for you in the status dictionary
        status = {'bad_name': {'status': 'hidden', 'message': 'This is my status message!'}}
        workflow_metas, warnings = self.run_update_status(status)

        self.assertEqual(1, len(warnings))
        self.assertEqual('missing_status', warnings[0].code)
        self.assertEqual('No status specified for workflow random_fact', warnings[0].message)

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
        self.assertEqual('Workflow \'random_fact\' can not be set to \'hide\', should be one of hidden,disabled,required,optional',
                         warnings[0].message)
