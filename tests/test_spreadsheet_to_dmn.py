from tests.base_test import BaseTest


class TestSStoDMN(BaseTest):

    def test_ss_to_dmn(self):
        self.load_example_data()
        workflow = self.create_workflow('spreadsheet_to_dmn')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        print(f'test_ss_to_dmn: task: {task}')