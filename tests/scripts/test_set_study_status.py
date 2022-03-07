from tests.base_test import BaseTest

from crc import session
from crc.models.study import StudyModel


class TestSetStudyStatus(BaseTest):

    def test_set_study_status(self):
        workflow = self.create_workflow('set_study_status')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        # assert we start with in_progress
        status = session.query(StudyModel.status).filter(StudyModel.id==workflow.study_id).scalar()
        self.assertEqual('in_progress', status.value)

        # the workflow sets the status to cr_connect_complete
        self.complete_form(workflow, task, {})

        status = session.query(StudyModel.status).filter(StudyModel.id==workflow.study_id).scalar()
        self.assertEqual('cr_connect_complete', status.value)
