from tests.base_test import BaseTest

from crc import connexion_app, session
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowModel
from crc.services.study_service import StudyService
from crc.services.workflow_spec_service import WorkflowSpecService

from unittest.mock import patch


class TestGetWaitingBCA(BaseTest):

    def test_get_waiting_bca(self):
        """Test the get_waiting_bca script.
        The script returns a list of all BCA workflows that are waiting for approval."""
        self.add_users()
        for spec in ['hello_world', 'billing_coverage_analysis']:
            # This creates a workflow using study_id 1, which it also creates if necessary.
            self.create_workflow(spec)

        #
        # at this point, there are 2 workflows in the db, with study_id 1
        #

        specs = WorkflowSpecService().get_specs()

        test_study_one = self.create_study(uid='kcm4zc', title='Test Study One')
        StudyService.add_all_workflow_specs_to_study(test_study_one, specs)

        test_study_two = self.create_study(uid='kcm4zc', title='Test Study Two')
        StudyService.add_all_workflow_specs_to_study(test_study_two, specs)

        test_study_three = self.create_study(uid='kcm4zc', title='Test Study Three')
        StudyService.add_all_workflow_specs_to_study(test_study_three, specs)

        #
        # There are 8 workflows in the db, 2 for each study. None are waiting bca
        #

        workflow = self.create_workflow('get_waiting_bca')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        assert task.data['waiting_bca'] == []

        bca_model = session.query(WorkflowModel). \
            filter(WorkflowModel.workflow_spec_id == 'billing_coverage_analysis'). \
            filter(WorkflowModel.study_id == test_study_one.id). \
            first()
        workflow_api = self.get_workflow_api(bca_model)
        task = workflow_api.next_task

        assert task.process_name == 'BCA Test'
        assert task.name == 'Activity_GetID'

        form_data = {'id': 1}
        workflow_api = self.complete_form(bca_model, task, form_data, user_uid='kcm4zc')

        saved_task = workflow_api.next_task

        assert saved_task.name == 'Activity_GetApprovalRequest'
        assert saved_task.lane == 'PIApprover'

        # Try to submit the form with a user_uid that is not in the lane
        form_data = {'case_id': 1, 'case_worker': 'Miss Information', 'notes': 'Test notes'}
        with self.assertRaises(AssertionError) as ae:
            self.complete_form(bca_model, saved_task, form_data, user_uid='kcm4zc')
        assert ae.exception.args[0] == ("False is not true : BAD Response: 400. \n "
                                        "This task must be completed by '['dhf8r', 'lb3dp']', "
                                        "but you are kcm4zc. . ")

        # We should have 2 waiting bca workflows now, one for each user in the lane
        workflow = self.create_workflow('get_waiting_bca')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        assert len(task.data['waiting_bca']) == 2
        for item in task.data['waiting_bca']:
            assert item['user_uid'] in ['dhf8r', 'lb3dp']

        # Complete the form with a valid user_uid. Either valid user can complete the task.
        self.complete_form(bca_model, saved_task, form_data, user_uid='lb3dp')

        # Check for waiting BCAs again. We should not have any now.
        workflow = self.create_workflow('get_waiting_bca')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        assert len(task.data['waiting_bca']) == 0
