from tests.base_test import BaseTest

from crc import session
from crc.models.workflow import WorkflowModel, WorkflowStatus
from crc.services.workflow_service import WorkflowService


class TestWaitingTaskError(BaseTest):

    def test_waiting_task_error(self):

        workflow = self.create_workflow('raise_error')
        workflow.status = WorkflowStatus.waiting
        session.commit()

        status_before = session.query(WorkflowModel.status).filter(WorkflowModel.id == workflow.id).scalar()
        WorkflowService.do_waiting()
        status_after = session.query(WorkflowModel.status).filter(WorkflowModel.id == workflow.id).scalar()

        self.assertEqual('waiting', status_before.value)
        self.assertEqual('erroring', status_after.value)
