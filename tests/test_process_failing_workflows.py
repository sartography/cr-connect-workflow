from tests.base_test import BaseTest

from crc import session
from crc.models.workflow import WorkflowStatus
from crc.services.workflow_service import WorkflowService


class TestFailingWorkflows(BaseTest):
    """Empty class DocString"""

    def test_failing_workflows(self):
        """We only test whether we have good information in the message.
        We do not test whether the message was sent by Sentry."""

        workflow_1 = self.create_workflow('random_fact')
        workflow_1.status = WorkflowStatus.erroring
        workflow_2 = self.create_workflow('random_fact')
        workflow_2.status = WorkflowStatus.erroring
        session.commit()
        message = WorkflowService().process_failing_workflows()
        self.assertIn('There are 2 workflows in an error state.', message)
        self.assertIn(f'workflow/{workflow_1.id}', message)
        self.assertIn(f'workflow/{workflow_2.id}', message)
