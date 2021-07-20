from tests.base_test import BaseTest

from crc import session
from crc.models.user import UserModel
from crc.services.workflow_service import WorkflowService

from example_data import ExampleDataLoader


class TestNoStudyWorkflow(BaseTest):

    def test_no_study_workflow(self):
        self.load_example_data()
        spec = ExampleDataLoader().create_spec('hello_world', 'Hello World', standalone=True, from_tests=True)
        user = session.query(UserModel).first()
        self.assertIsNotNone(user)
        workflow_model = WorkflowService.get_workflow_from_spec(spec.id, user)
        workflow_api = self.get_workflow_api(workflow_model)
        first_task = workflow_api.next_task
        self.complete_form(workflow_model, first_task, {'name': 'Big Guy'})
        workflow_api = self.get_workflow_api(workflow_model)
        second_task = workflow_api.next_task
        self.assertEqual(second_task.documentation, 'Hello Big Guy')
