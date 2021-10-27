from tests.base_test import BaseTest

from crc import session
from crc.models.task_log import TaskLogModel


class TestLoggingScript(BaseTest):

    def test_logging_script(self):
        workflow = self.create_workflow('logging_task')
        workflow_api = self.get_workflow_api(workflow)
        task = workflow_api.next_task

        log_id = task.data['log_model']['id']
        log_model = session.query(TaskLogModel).filter(TaskLogModel.id == log_id).first()

        self.assertEqual('test_code', log_model.code)
        self.assertEqual('info', log_model.level)
        self.assertEqual('Activity_LogEvent', log_model.task)
