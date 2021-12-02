from tests.base_test import BaseTest


class TestGetStudyStatus(BaseTest):

    def test_get_study_status(self):
        workflow = self.create_workflow('get_study_status')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        self.assertEqual(task.data['study_status'], workflow.study.status.value)

        print('test_get_study_status')
