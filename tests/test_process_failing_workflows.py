from tests.base_test import BaseTest

from crc import session
from crc.models.email import EmailModel
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
        WorkflowService().process_failing_workflows()

        mail_messages = EmailModel.query.filter(EmailModel.name == 'failing_workflows').all()
        assert len(mail_messages) == 1
        assert mail_messages[0].subject == 'Failing CRC Workflows'
        assert (mail_messages[0].content ==
                "There are 2 failing workflows.\n\n"
                "[https://localhost:4200/workflow/1](https://localhost:4200/workflow/1)\n"
                "[https://localhost:4200/workflow/2](https://localhost:4200/workflow/2)")
