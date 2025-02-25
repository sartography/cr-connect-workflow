from tests.base_test import BaseTest

from crc import connexion_app, session
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowModel
from crc.services.study_service import StudyService
from crc.services.workflow_spec_service import WorkflowSpecService

from unittest.mock import patch


class TestGetWaitingBCA(BaseTest):

    def test_get_waiting_bca(self):
        """The get_waiting_bca script returns a list of all BCA workflows that are waiting for approval."""
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

        workflow_model = session.query(WorkflowModel). \
            filter(WorkflowModel.workflow_spec_id == 'billing_coverage_analysis'). \
            filter(WorkflowModel.study_id == test_study_one.id). \
            first()
        workflow_model.status = 'waiting'
        session.commit()

        workflow = self.create_workflow('get_waiting_bca')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        assert len(task.data['waiting_bca']) == 1

        workflow_model = session.query(WorkflowModel). \
            filter(WorkflowModel.workflow_spec_id == 'billing_coverage_analysis'). \
            filter(WorkflowModel.study_id == test_study_three.id). \
            first()
        workflow_model.status = 'waiting'

        workflow = self.create_workflow('get_waiting_bca')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        assert len(task.data['waiting_bca']) == 2
