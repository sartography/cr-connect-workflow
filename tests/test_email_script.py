from tests.base_test import BaseTest
from crc import mail


# class TestEmailDirectly(BaseTest):
#
#     def test_email_directly(self):
#         recipients = ['michaelc@cullerton.com']
#         sender = 'michaelc@cullerton.com'
#         with mail.record_messages() as outbox:
#             mail.send_message(subject='testing',
#                               body='test',
#                               recipients=recipients,
#                               sender=sender)
#             assert len(outbox) == 1
#             assert outbox[0].subject == "testing"


class TestEmailScript(BaseTest):

    def test_email_script(self):
        with mail.record_messages() as outbox:

            workflow = self.create_workflow('email_script')

            first_task = self.get_workflow_api(workflow).next_task
            # self.assertEqual('Activity_GetData', first_task.name)
            workflow = self.get_workflow_api(workflow)
            self.complete_form(workflow, first_task, {'email_address': 'michaelc@cullerton.com'})

            self.assertEqual(1, len(outbox))
            self.assertEqual("My Email Subject", outbox[0].subject)
