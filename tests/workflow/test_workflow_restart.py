from tests.base_test import BaseTest

from crc import session
from crc.models.study import StudyModel

class TestWorkflowRestart(BaseTest):

    def test_workflow_restart(self):

        workflow = self.create_workflow('message_event')

        first_task = self.get_workflow_api(workflow).next_task
        self.assertEqual('Activity_GetData', first_task.name)
        workflow_api = self.get_workflow_api(workflow)

        result = self.complete_form(workflow_api, first_task, {'formdata': 'asdf'})
        self.assertIn('formdata', result.next_task.data)
        self.assertEqual('asdf', result.next_task.data['formdata'])

        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual('Activity_HowMany', self.get_workflow_api(workflow_api).next_task.name)

        # restart with data. should land at beginning with data
        workflow_api = self.restart_workflow_api(result)
        first_task = self.get_workflow_api(workflow_api).next_task
        self.assertEqual('Activity_GetData', first_task.name)
        self.assertIn('formdata', workflow_api.next_task.data)
        self.assertEqual('asdf', workflow_api.next_task.data['formdata'])

        # restart without data.
        workflow_api = self.restart_workflow_api(workflow_api, clear_data=True)
        first_task = self.get_workflow_api(workflow).next_task
        self.assertEqual('Activity_GetData', first_task.name)
        self.assertNotIn('formdata', workflow_api.next_task.data)

        print('Nice Test')

    def test_workflow_restart_on_cancel_notify(self):
        workflow = self.create_workflow('message_event')
        study_id = workflow.study_id

        # Start the workflow.
        first_task = self.get_workflow_api(workflow).next_task
        self.assertEqual('Activity_GetData', first_task.name)
        workflow_api = self.get_workflow_api(workflow)
        self.complete_form(workflow_api, first_task, {'formdata': 'asdf'})
        workflow_api = self.get_workflow_api(workflow)
        self.assertEqual('Activity_HowMany', workflow_api.next_task.name)

        workflow_api = self.restart_workflow_api(workflow)
        study_result = session.query(StudyModel).filter(StudyModel.id == study_id).first()
        self.assertEqual('New Title', study_result.title)

    def test_workflow_restart_before_cancel_notify(self):
        workflow = self.create_workflow('message_event')
        study_id = workflow.study_id

        first_task = self.get_workflow_api(workflow).next_task
        self.assertEqual('Activity_GetData', first_task.name)

        study_result = session.query(StudyModel).filter(StudyModel.id == study_id).first()
        self.assertEqual('Beer consumption in the bipedal software engineer', study_result.title)

    def test_workflow_restart_after_cancel_notify(self):
        workflow = self.create_workflow('message_event')
        study_id = workflow.study_id

        # Start the workflow.
        first_task = self.get_workflow_api(workflow).next_task
        self.assertEqual('Activity_GetData', first_task.name)
        workflow_api = self.get_workflow_api(workflow)
        self.complete_form(workflow_api, first_task, {'formdata': 'asdf'})

        workflow_api = self.get_workflow_api(workflow)
        next_task = workflow_api.next_task
        self.assertEqual('Activity_HowMany', next_task.name)
        self.complete_form(workflow_api, next_task, {'how_many': 3})

        workflow_api = self.restart_workflow_api(workflow)
        study_result = session.query(StudyModel).filter(StudyModel.id == study_id).first()
        self.assertEqual('Beer consumption in the bipedal software engineer', study_result.title)

