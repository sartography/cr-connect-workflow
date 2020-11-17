from tests.base_test import BaseTest
from crc.models.study import StudyModel
from crc import db


class TestMessageEvent(BaseTest):

    def test_message_event(self):

        workflow = self.create_workflow('message_event')
        study_id = workflow.study_id

        # Start the workflow.
        first_task = self.get_workflow_api(workflow).next_task
        self.assertEqual('Activity_GetData', first_task.name)
        workflow = self.get_workflow_api(workflow)
        self.complete_form(workflow, first_task, {'formdata': 'asdf'})
        workflow = self.get_workflow_api(workflow)
        self.assertEqual('Activity_HowMany', workflow.next_task.name)

        # reset the workflow
        # this ultimately calls crc.api.workflow.set_current_task
        self.app.put('/v1.0/workflow/%i/task/%s/set_token' % (
                     workflow.id,
                     first_task.id),
                     headers=self.logged_in_headers(),
                     content_type="application/json")

        # set_current_task should call the interupt (signal) task
        # which should run the script in our task
        #
        # test to see if our changes made it to the DB
        study_result = db.session.query(StudyModel).filter(StudyModel.id == study_id).first()
        self.assertEqual(study_result.title, 'New Title')
