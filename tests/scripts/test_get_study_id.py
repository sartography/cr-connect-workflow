from tests.base_test import BaseTest


class TestGetStudyId(BaseTest):

    def test_get_study_id(self):
        workflow = self.create_workflow('get_study_id')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        self.assertEqual(task.data['current_study_id'], workflow.study.id)
