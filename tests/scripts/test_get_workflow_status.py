from tests.base_test import BaseTest

from crc import session
from crc.models.workflow import WorkflowModel


class TestGetWorkflowStatus(BaseTest):

    def test_get_workflow_status_validation(self):
        self.load_example_data()
        spec_model = self.load_test_spec('get_workflow_status')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)

    def test_get_workflow_status(self):
        self.load_example_data()
        workflow_model_1 = session.query(WorkflowModel).filter(WorkflowModel.id == 1).first()
        search_workflow_id = workflow_model_1.id
        workflow = self.create_workflow('get_workflow_status')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        # calls get_workflow_status(search_workflow_id)
        workflow_api = self.complete_form(workflow, task, {'search_workflow_id': search_workflow_id})
        task = workflow_api.next_task
        self.assertEqual('Activity_StatusArg', task.name)
        self.assertEqual(task.data['status_arg'], workflow_model_1.status.value)

        # calls get_workflow_status(search_workflow_id=search_workflow_id)
        workflow_api = self.complete_form(workflow, task, {})
        task = workflow_api.next_task
        self.assertEqual('Activity_StatusKwarg', task.name)
        self.assertEqual(task.data['status_kwarg'], workflow_model_1.status.value)


