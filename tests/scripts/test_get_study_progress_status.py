from tests.base_test import BaseTest

from crc import session
from crc.models.study import StudyModel, ProgressStatus


class TestGetStudyProgressStatus(BaseTest):

    def test_get_study_progress_status(self):
        workflow = self.create_workflow('get_study_progress_status')
        study_model = session.query(StudyModel).filter(StudyModel.id == workflow.study_id).first()
        study_model.progress_status = ProgressStatus.approved
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        self.assertEqual(task.data['study_progress_status'], workflow.study.progress_status.value)
