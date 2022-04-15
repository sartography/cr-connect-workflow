from tests.base_test import BaseTest

from crc import session
from crc.models.study import StudyModel
from crc.models.workflow import WorkflowModel
from crc.services.study_service import StudyService
from crc.services.workflow_spec_service import WorkflowSpecService


class TestStartWorkflow(BaseTest):

    def setup_test_start_workflow(self):
        self.add_users()
        self.create_workflow('hello_world')
        workflow_spec_to_start = WorkflowSpecService().get_spec('hello_world')

        workflow = self.create_workflow('start_workflow')
        study_id = workflow.study_id
        study = session.query(StudyModel).filter(StudyModel.id==study_id).first()
        StudyService.add_all_workflow_specs_to_study(study, [workflow_spec_to_start])

        return workflow

    def test_start_workflow_validation(self):
        random_wf = self.create_workflow('random_fact') # Assure we have a workflow to start.
        spec_model = self.load_test_spec('start_workflow')
        rv = self.app.get('/v1.0/workflow-specification/%s/validate' % spec_model.id, headers=self.logged_in_headers())
        self.assertEqual([], rv.json)

    def test_start_workflow(self):
        workflow = self.setup_test_start_workflow()

        workflow_before = session.query(WorkflowModel).filter(WorkflowModel.workflow_spec_id=='hello_world').first()
        self.assertEqual('not_started', workflow_before.status.value)

        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        self.complete_form(workflow, task, {'workflow_spec_to_start': 'hello_world'})

        workflow_after = session.query(WorkflowModel).filter(WorkflowModel.workflow_spec_id=='hello_world').first()
        self.assertEqual('user_input_required', workflow_after.status.value)

    def test_bad_workflow_spec_id(self):
        workflow = self.setup_test_start_workflow()
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        with self.assertRaises(AssertionError) as e:
            self.complete_form(workflow, task, {'workflow_spec_to_start': 'bad_spec_id'})
