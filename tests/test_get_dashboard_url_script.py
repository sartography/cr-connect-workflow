from tests.base_test import BaseTest
from crc import app, mail


class TestGetDashboardURL(BaseTest):

    def test_get_dashboard_url(self):
        with mail.record_messages() as outbox:

            dashboard_url = f'https://{app.config["FRONTEND"]}'
            workflow = self.create_workflow('email_dashboard_url')
            self.get_workflow_api(workflow)

            self.assertEqual(1, len(outbox))
            self.assertEqual('My Email Subject', outbox[0].subject)
            self.assertEqual(['test@example.com'], outbox[0].recipients)
            self.assertIn(dashboard_url, outbox[0].body)
