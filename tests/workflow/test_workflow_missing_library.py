from tests.base_test import BaseTest
from example_data import ExampleDataLoader


class TestDuplicateWorkflowSpecFile(BaseTest):

    def test_duplicate_workflow_spec_file(self):
        spec1 = ExampleDataLoader().create_spec('missing_library', 'Missing Library', category_id=0, library=False,
                                               from_tests=True)
        workflow = self.create_workflow('missing_library')
        with self.assertRaises(AssertionError) as ae:
            workflow_api = self.get_workflow_api(workflow)
        # task = workflow_api.next_task
        #     self.complete_form(workflow, task, {'num_1': 4, 'num_2': 5})

        print('test_duplicate_workflow_spec_file')