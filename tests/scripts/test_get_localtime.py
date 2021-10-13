from tests.base_test import BaseTest
from crc.models.file import FileDataModel
from crc import session


class TestGetLocaltime(BaseTest):

    def test_get_localtime(self):
        self.load_example_data()
        # file_model = session.query(FileDataModel).first()
        # test_time = file_model.date_created

        workflow = self.create_workflow('get_localtime')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task
        # workflow_api = self.complete_form(workflow, task, {'timestamp': test_time})

        # local_time =

        print('test_get_localtime')

